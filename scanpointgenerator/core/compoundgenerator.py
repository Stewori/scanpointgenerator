import logging
import numpy as np
from threading import Lock

from scanpointgenerator.compat import range_
from scanpointgenerator.core.generator import Generator
from scanpointgenerator.core.point import Point
from scanpointgenerator.core.excluder import Excluder
from scanpointgenerator.core.mutator import Mutator


@Generator.register_subclass("scanpointgenerator:generator/CompoundGenerator:1.0")
class CompoundGenerator(Generator):
    """Nest N generators, apply exclusion regions to relevant generator pairs
    and apply any mutators before yielding points"""

    def __init__(self, generators, excluders, mutators):
        """
        Args:
            generators(list(Generator)): List of Generators to nest
            excluders(list(Excluder)): List of Excluders to filter points by
            mutators(list(Mutator)): List of Mutators to apply to each point
        """

        self.excluders = excluders
        self.mutators = mutators
        self.axes = []
        self.position_units = {}
        self.axes_points = {}
        self.axes_points_lower = {}
        self.axes_points_upper = {}
        self.dimensions = []
        self.alternate_direction = [g.alternate_direction for g in generators]
        for generator in generators:
            logging.debug("Generator passed to Compound init")
            logging.debug(generator.to_dict())
            if isinstance(generator, self.__class__):
                raise TypeError("CompoundGenerators cannot be nested, nest"
                                "its constituent parts instead")
            self.axes += generator.axes
            self.position_units.update(generator.position_units)
        if len(self.axes) != len(set(self.axes)):
            raise ValueError("Axis names cannot be duplicated")

        self.generators = generators
        self.generator_dim_scaling = {}

    def prepare(self):
        self.num = 1
        self.dimensions = []
        for generator in self.generators:
            generator.produce_points()
            self.axes_points.update(generator.points)
            self.axes_points_lower.update(generator.points_lower)
            self.axes_points_upper.update(generator.points_upper)
            self.num *= generator.num

            dim = {"size":generator.num,
                "axes":list(generator.axes),
                "generators":[generator],
                "masks":[],
                "tile":1,
                "repeat":1,
                "alternate":generator.alternate_direction}
            self.dimensions.append(dim)

        for excluder in self.excluders:
            axis_1, axis_2 = excluder.scannables
            # ensure axis_1 is "outer" axis (if separate generators)
            gen_1 = [g for g in self.generators if axis_1 in g.axes][0]
            gen_2 = [g for g in self.generators if axis_2 in g.axes][0]
            gen_diff = self.generators.index(gen_1) \
                - self.generators.index(gen_2)
            if gen_diff < -1 or gen_diff > 1:
                raise ValueError(
                    "Excluders must be defined on axes that are adjacent in " \
                        "generator order")
            if gen_diff == 1:
                gen_1, gen_2 = gen_2, gen_1
                axis_1, axis_2 = axis_2, axis_1
                gen_diff = -1


            #####
            # first check if region spans two dimensions - merge if so
            #####
            dim_1 = [i for i in self.dimensions if axis_1 in i["axes"]][0]
            dim_2 = [i for i in self.dimensions if axis_2 in i["axes"]][0]
            dim_diff = self.dimensions.index(dim_1) \
                - self.dimensions.index(dim_2)
            if dim_1["alternate"] != dim_2["alternate"]:
                raise ValueError(
                    "Generators tied by regions must have the same " \
                            "alternate_direction setting")
            # merge "inner" into "outer"
            if dim_diff < -1 or dim_diff > 1:
                raise ValueError(
                    "Excluders must be defined on axes that are adjacent in " \
                        "generator order")
            if dim_diff == 1:
                dim_1, dim_2 = dim_2, dim_1
                dim_diff = -1
            if dim_diff == -1:
                # dim_1 is "outer" - preserves axis ordering

                # need to appropriately scale the existing masks
                # masks are "tiled" by the size of generators "below" them
                # and their elements are "repeated" by the size of generators
                # above them, so:
                # |mask| * duplicates * repeates == |generators in index|
                scale = 1
                for g in dim_2["generators"]:
                    scale *= g.num
                for m in dim_1["masks"]:
                    m["repeat"] *= scale
                scale = 1
                for g in dim_1["generators"]:
                    scale *= g.num
                for m in dim_2["masks"]:
                    m["tile"] *= scale
                dim_1["masks"] += dim_2["masks"]
                dim_1["axes"] += dim_2["axes"]
                dim_1["generators"] += dim_2["generators"]
                dim_1["size"] *= dim_2["size"]
                self.dimensions.remove(dim_2)
            dim = dim_1

            #####
            # generate the mask for this region
            #####
            # if gen_1 and gen_2 are different then the outer axis will have to
            # have its elements repeated and the inner axis will have to have
            # itself repeated - gen_1 is always inner axis

            points_1 = self.axes_points[axis_1]
            points_2 = self.axes_points[axis_2]

            doubled_mask = False # used for some cases of alternating generators

            if gen_1 is gen_2 and dim["alternate"]:
                # run *both* axes backwards
                # but our mask will be a factor of 2 too big
                doubled_mask = True
                points_1 = np.append(points_1, points_1[::-1])
                points_2 = np.append(points_2, points_2[::-1])
            elif dim["alternate"]:
                doubled_mask = True
                points_1 = np.append(points_1, points_1[::-1])
                points_2 = np.append(points_2, points_2[::-1])
                points_2 = np.tile(points_2, gen_1.num)
                points_1 = np.repeat(points_1, gen_2.num)
            elif gen_1 is not gen_2:
                points_1 = np.repeat(points_1, gen_2.num)
                points_2 = np.tile(points_2, gen_1.num)
            # else not needed; do nothing if gen_1 is gen_2 and not alternating


            if axis_1 == excluder.scannables[0]:
                mask = excluder.create_mask(points_1, points_2)
            else:
                mask = excluder.create_mask(points_2, points_1)

            #####
            # Add new mask to index
            #####
            tile = 0.5 if doubled_mask else 1
            repeat = 1
            found_axis = False
            # tile by product of generators "before"
            # repeat by product of generators "after"
            for g in dim["generators"]:
                if axis_1 in g.axes or axis_2 in g.axes:
                    found_axis = True
                else:
                    if found_axis:
                        repeat *= g.num
                    else:
                        tile *= g.num
            m = {"repeat":repeat, "tile":tile, "mask":mask}
            dim["masks"].append(m)
        # end for excluder in self.excluders
        #####

        tile = 1
        repeat = 1
        #####
        # Generate full index mask and "apply"
        #####
        for dim in self.dimensions:
            mask = np.full(dim["size"], True, dtype=np.bool)
            for m in dim["masks"]:
                assert len(m["mask"]) * m["repeat"] * m["tile"] == len(mask), \
                        "Mask lengths are not consistent"
                expanded = np.repeat(m["mask"], m["repeat"])
                if m["tile"] % 1 != 0:
                    ex = np.tile(expanded, int(m["tile"]))
                    expanded = np.append(ex, expanded[:len(expanded)//2])
                else:
                    expanded = np.tile(expanded, int(m["tile"]))
                mask &= expanded
            dim["mask"] = mask
            dim["indicies"] = np.flatnonzero(mask)
            if len(dim["indicies"]) == 0:
                raise ValueError("Regions would exclude entire scan")
            repeat *= len(dim["indicies"])
        self.num = repeat
        for dim in self.dimensions:
            l = len(dim["indicies"])
            repeat /= l
            dim["tile"] = tile
            dim["repeat"] = repeat
            tile *= l

        for dim in self.dimensions:
            tile = 1
            repeat = 1
            for g in dim["generators"]:
                repeat *= g.num
            for g in dim["generators"]:
                repeat /= g.num
                d = {"tile":tile, "repeat":repeat}
                tile *= g.num
                self.generator_dim_scaling[g] = d

    def iterator(self):
        it = (self.get_point(n) for n in range_(self.num))
        for m in self.mutators:
            it = m.mutate(it)
        for p in it:
            yield p

    def get_point(self, n):
        if n >= self.num:
            raise IndexError("Requested point is out of range")
        p = Point()

        # need to know how far along each index we are
        # and, in the case of alternating indicies, how
        # many times we've run through them
        kc = 0 # the "cumulative" k for each index
        for dim in self.dimensions:
            indicies = dim["indicies"]
            i = n // dim["repeat"]
            r = i // len(indicies)
            i %= len(indicies)
            k = indicies[i]
            dim_reverse = False
            if dim["alternate"] and kc % 2 == 1:
                i = len(indicies) - i - 1
                dim_reverse = True
            kc *= len(indicies)
            kc += k
            k = indicies[i]
            # need point k along each generator in index
            # in alternating case, need to sometimes go backward
            p.indexes.append(i)
            for g in dim["generators"]:
                j = k // self.generator_dim_scaling[g]["repeat"]
                gr = j // g.num
                j %= g.num
                if dim["alternate"] and g is not dim["generators"][0] and gr % 2 == 1:
                    j = g.num - j - 1
                for axis in g.axes:
                    p.positions[axis] = g.points[axis][j]
                    p.lower[axis] = g.points_lower[axis][j]
                    p.upper[axis] = g.points_upper[axis][j]
        return p

    def to_dict(self):
        """Convert object attributes into a dictionary"""
        d = {}
        d['typeid'] = self.typeid
        d['generators'] = [g.to_dict() for g in self.generators]
        d['excluders'] = [e.to_dict() for e in self.excluders]
        d['mutators'] = [m.to_dict() for m in self.mutators]
        return d

    @classmethod
    def from_dict(cls, d):
        """
        Create a CompoundGenerator instance from a serialised dictionary
        Args:
            d(dict): Dictionary of attributes
        Returns:
            CompoundGenerator: New CompoundGenerator instance
        """
        generators = [Generator.from_dict(g) for g in d['generators']]
        excluders = [Excluder.from_dict(e) for e in d['excluders']]
        mutators = [Mutator.from_dict(m) for m in d['mutators']]
        return cls(generators, excluders, mutators)
