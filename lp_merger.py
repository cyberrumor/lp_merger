#!/usr/bin/env python3
import sys
import argparse
import json
from pathlib import Path
from dataclasses import (
    dataclass,
    asdict,
    field,
)
from enum import StrEnum
from copy import deepcopy


class Flag(StrEnum):
    IGNORE_SCALE = "IgnoreScale"
    NO_EXTERNAL_EMITTANCE = "NoExternalEmittance"
    PORTAL_STRICT = "PortalStrict"
    RANDOM_ANIM_START = "RandomAnimStart"
    SHADOW = "Shadow"
    SIMPLE = "Simple"
    SYNC_ADDON_NODES = "SyncAddonNodes"
    UPDATE_ON_CELL_TRANSITION = "UpdateOnCellTransition"
    UPDATE_ON_WAITING = "UpdateOnWaiting"


def get_flag(string: str) -> Flag:
    """
    Return a flag enum representation of a case-insensitive string.
    """
    flag_map = {
        "ignorescale": Flag.IGNORE_SCALE,
        "noexternalemittance": Flag.NO_EXTERNAL_EMITTANCE,
        "portalstrict": Flag.PORTAL_STRICT,
        "randomanimstart": Flag.RANDOM_ANIM_START,
        "shadow": Flag.SHADOW,
        "simple": Flag.SIMPLE,
        "syncaddonnodes": Flag.SYNC_ADDON_NODES,
        "updateoncelltransition": Flag.UPDATE_ON_CELL_TRANSITION,
        "updateonwaiting": Flag.UPDATE_ON_WAITING
    }

    return flag_map[string.lower()]


class Interpolation(StrEnum):
    CUBIC = "Cubic"
    LINEAR = "Linear"
    STEP = "Step"


def get_interpolation(string: str) -> Interpolation:
    """
    Return an interpolation enum representation of a case-insensitive string.
    """
    interpolation_map = {
        "cubic": Interpolation.CUBIC,
        "linear": Interpolation.LINEAR,
        "step": Interpolation.STEP,
    }
    return interpolation_map[string.lower()]


class AttachmentType(StrEnum):
    ADDON_NODES = "addonNodes"
    MODELS = "models"
    VISUAL_EFFECTS = "visualEffects"


type Color = list[float] | list[int]

@dataclass(kw_only=True)
class Keyframe:
    backward: float
    forward: float
    time: float
    value: float


@dataclass(kw_only=True)
class PositionController:
    backward: float
    forward: float
    time: float
    translation: list[float]


@dataclass(kw_only=True)
class RotationController:
    backward: float
    forward: float
    rotation: list[float]
    time: float


@dataclass(kw_only=True)
class ColorController:
    color: Color
    time: float


@dataclass(kw_only=True)
class RadiusController:
    interpolation: Interpolation
    keys: list[Keyframe]


@dataclass(kw_only=True)
class FadeController:
    interpolation: Interpolation
    keys: list[Keyframe]


@dataclass(kw_only=True)
class Data:
    light: str

    color: Color | None = None
    colorController: ColorController | None = None
    conditionalNodes: list[str] | None = None
    conditions: list[str] | None = None
    externalEmittance: str | None = None
    fade: float | None = None
    fadeController: FadeController | None = None
    flags: list[Flag] | None = None
    fov: float | None = None
    offset: list[float] | None = None
    positionController: PositionController | None = None
    radius: float | None = None
    radiusController: RadiusController | None = None
    rotation: list[float] | None = None
    rotationController: RotationController | None = None
    shadowDepthBias: float | None = None

    def __post_init__(self):
        if self.rotation is not None:
            for i in self.rotation:
                while abs(i) >= 360:
                    # Converge astronomic degrees towards their smallest
                    # equivalent representation.
                    if i > 0:
                        i -= 360
                    elif i < 0:
                        i += 360
                    else:
                        break

        if self.flags:
            # This will have been cast into a plain string, but
            # we want to separate and compare these flags,
            # asserting that they're a valid enum. Cast them
            # to list[Flag]
            flags = self.flags.split("|")
            for flag in flags:
                flag = get_flag(flag)

            self.flags = flags


            if Flag.SHADOW in self.flags:
                assert (
                    self.shadowDepthBias is not None
                ), "'Shadow' flag present but no 'shadowDepthBias' set"

        if self.shadowDepthBias is not None:
            assert (
                self.flags and Flag.SHADOW in self.flags
            ), "'shadowDepthBias' set without 'Shadow' flag"


@dataclass(kw_only=True)
class Light:
    data: Data

    blackList: list[str] | None = None
    nodes: list[str] | None = None
    points: list[list[float]] | None = None
    whiteList: list[str] | None = None

    def __post_init__(self):

        if self.blackList is not None:
            self.blackList = sorted([i.lower() for i in self.blackList])

        if self.whiteList is not None:
            self.whiteList = sorted([i.lower() for i in self.whiteList])

        if self.points is not None:
            for i in self.points:
                assert (
                    len(i) == 3
                ), f"Expected 'points' to have 3 items, found {i}"

            self.points = sorted(
                self.points,
                key=lambda x: (x[0], x[1], x[2])
            )


@dataclass(kw_only=True)
class Entry:
    lights: list[Light]

    addonNodes: list[int] | None = field(compare=False, default=None)
    models: list[str] | None = field(compare=False, default=None)
    visualEffects: list[str] | None = field(compare=False, default=None)

    attachment_type: AttachmentType = field(init=False)

    def __post_init__(self):
        assert (
            any((self.models, self.addonNodes, self.visualEffects))
        ), "Entry didn't define keys for models, addonNodes, or visualEffects. At least one is required."

        if self.models:
            self.attachment_type = AttachmentType.MODELS
            self.models.sort()

            for light in self.lights:
                assert (light.points or light.nodes)

        if self.addonNodes:
            self.attachment_type = AttachmentType.ADDON_NODES
            self.addonNodes.sort()

        if self.visualEffects:
            self.attachment_type = AttachmentType.VISUAL_EFFECTS
            self.visualEffects.sort()


def get_entries_from(path: Path) -> list[Entry]:
    """
    Given a file path, serialize the file into a list of Entries
    and return it.
    """
    with open(path, "r", encoding="utf-8") as f:
        contents = json.loads(f.read())

    result: list[Entry] = []

    for item in contents:
        entry = Entry(
            lights=[
                Light(
                    blackList=light.get("blackList", None),
                    data=Data(
                        color=light["data"].get("color", None),
                        colorController=light["data"].get("colorController", None),
                        conditionalNodes=light["data"].get("conditionalNodes", None),
                        conditions=light["data"].get("conditions", None),
                        externalEmittance=light["data"].get("externalEmittance", None),
                        fade=light["data"].get("fade", None),
                        flags=light["data"].get("flags", None),
                        fov=light["data"].get("fov", None),
                        light=light["data"].get("light"),
                        offset=light["data"].get("offset", None),
                        positionController=light["data"].get("positionController", None),
                        radius=light["data"].get("radius", None),
                        radiusController=light["data"].get("radiusController", None),
                        rotation=light["data"].get("rotation", None),
                        rotationController=light["data"].get("rotationController", None),
                        shadowDepthBias=light["data"].get("shadowDepthBias", None),
                    ),
                    nodes=light.get("nodes", None),
                    points=light.get("points", None),
                    whiteList=light.get("whiteList", None),
                )
                for light in item["lights"]
            ],
            visualEffects=item.get("visualEffects", None),
            addonNodes=[int(addonNode) for addonNode in item.get("addonNodes", [])] or None,
            models=item.get("models", None),
        )

        result.append(entry)

    return result


def parse_args(sys_argv: list[str]) -> argparse.Namespace:
    """
    Arg parser.
    """
    parser = argparse.ArgumentParser(prog=Path(__file__).name)
    parser.add_argument(
        "paths",
        type=Path,
        nargs="*",
        help="list of paths to files under 'Data/lightplacer/'. Earlier files win model/addonNode conflicts.",
    )
    return parser.parse_args()


def expand(entry: Entry) -> list[Entry]:
    """
    Given a single entry, return a list of entries where each
    entry contains only one model, addonNode, or visualEffect
    from the original entry.
    """
    result = []
    for attr in ("addonNodes", "models", "visualEffects"):
        if (a := getattr(entry, attr)) is not None and len(a) > 0:
            for item in a:
                new_entry = deepcopy(entry)
                setattr(new_entry, attr, [item])
                result.append(new_entry)
            return result

    # Couldn't expand, just return what we got as a list.
    return [entry]


def collapse(entries :list[Entry]) -> list[Entry]:
    """
    We have a list of entries where each model,
    addonNode, or visualEffect resides in its own entry.
    For each entry, if that entry could be represented
    perfectly by another, merge them.

    Return a new list of those entries.
    """
    result: list[Entry] = []

    for index, entry in enumerate(entries):

        for other_entry in entries[index + 1:]:
            if entry == other_entry:
                if (
                    (original := getattr(entry, entry.attachment_type, None))
                    and
                    (new := getattr(other_entry, other_entry.attachment_type, None))
                ):
                    original.extend(new)

        if entry not in result:
            result.append(entry)

    return result


def serialize[T](iterable: T) -> T:
    """
    Return a new dict:
        - without null-keys,
        - with list[Flag] as 'flag1|flag2|flag3'
        - without .attachment_type
    """
    if isinstance(iterable, list):
        result = []
        for i in iterable:
            result.append(serialize(i))
        return result

    elif isinstance(iterable, dict):
        result = {}
        for k, v in iterable.items():
            if v is None:
                continue

            if k == "attachment_type":
                continue

            if k == "flags":
                # Change from:
                # "flags": ["IgnoreScale", "Shadow"]
                # to
                # "flags": "IgnoreScale|Shadow"
                v.sort()
                v = "|".join(v)

            v = serialize(v)

            result[k] = v

        return result

    return iterable


def main(sys_argv: list[str]):
    args = parse_args(sys_argv)

    config: list[Entry] = []

    for path in args.paths:
        assert path.absolute().exists()

    for path in args.paths:
        lightplacerconf = get_entries_from(path)
        config.extend(lightplacerconf)

    expanded_config: list[Entry] = []
    for entry in config:
        expanded_config.extend(expand(entry))

    deduped_config: list[Entry] = []
    for entry in expanded_config:
        for attr in ("addonNodes", "models", "visualEffects"):
            if (a := getattr(entry, attr)) is not None and len(a) > 0:
                if a[0] not in (getattr(i, attr) for i in deduped_config):
                    deduped_config.append(entry)

    sorted_config = sorted(
        deduped_config,
        key=lambda x: (
            (getattr(x, "addonNodes", [0]) or [0])[0],
            (getattr(x, "models", [""]) or [""])[0].lower(),
            (getattr(x, "visualEffects", [0]) or [0])[0],
        )
    )

    clean_config = [serialize(asdict(entry)) for entry in collapse(sorted_config)]
    print(json.dumps(clean_config, sort_keys=True, indent=2))


if __name__ == "__main__":
    main(sys.argv)
