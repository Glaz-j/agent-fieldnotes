# Third-party notices and source provenance

The original code, documentation, and scene additions in this reproduction package are distributed under the Apache License, Version 2.0, in [LICENSE](LICENSE). Third-party files retain their respective licenses below. In particular, the bundled Inter font remains under the SIL Open Font License and is not relicensed under Apache 2.0.

## SO-101 robot description and mesh assets

- Project: **Standard Open SO-100 & SO-101 Arms**, TheRobotStudio/SO-ARM100.
- Repository: <https://github.com/TheRobotStudio/SO-ARM100>.
- Pinned revision: `eecbe3e0a9ebb23e25ad7b2759b03884c6660903` (2026-09-06).
- Source directory: [`Simulation/SO101/`](https://github.com/TheRobotStudio/SO-ARM100/tree/eecbe3e0a9ebb23e25ad7b2759b03884c6660903/Simulation/SO101).
- License: **Apache License, Version 2.0**. The package's [LICENSE](LICENSE) is an exact copy of the upstream [LICENSE at the pinned revision](https://github.com/TheRobotStudio/SO-ARM100/blob/eecbe3e0a9ebb23e25ad7b2759b03884c6660903/LICENSE).
- Local unmodified source: `assets/so101/so101_new_calib.xml` and its 13 referenced STL meshes in `assets/so101/assets/`.

These vendored XML and STL files were checked byte-for-byte against the pinned upstream Git revision. The upstream tree has no separate `NOTICE` file or nested license for `Simulation/SO101` at that revision. Redistribution and modification of these assets remain subject to the Apache 2.0 terms, including retention of applicable notices and prominent modification notices in changed files.

The package's scene-building code derives the runnable robot XML from this vendored source. It changes the mesh location, collision friction and contact dimensions, fingertip collision representation, and gripper force limit, and adds visible contact pads, a grasp site, and a visual calibration marker. The resulting robot XML is a modified derivative; the original vendored XML and STL meshes remain unchanged. Refer to the builder and generated XML for the actual parameter values.

### Preserved upstream provenance

The upstream robot XML begins with these notices:

```text
Generated using onshape-to-robot
Onshape https://cad.onshape.com/documents/7715cc284bb430fe6dab4ffd/w/4fd0791b683777b02f8d975a/e/826c553ede3b7592eb9ca800
```

Its actuator-gain comment states:

```text
These gains are not a 1-to-1 mapping of the servo gains used in
Lerobot. These position gains and forces were calculated according to
https://github.com/Gregory119/RBE501-RL-arm-project/blob/main/gymnasium_env/README.md,
assuming that the servo proportional gain is set to 16.
```

The upstream [SO-101 description README](https://github.com/TheRobotStudio/SO-ARM100/blob/eecbe3e0a9ebb23e25ad7b2759b03884c6660903/Simulation/SO101/README.md) also credits the [onshape-to-robot](https://github.com/Rhoban/onshape-to-robot) generator and states:

> Motor properties for the STS3215 motors used in the robot are adapted from the [Open Duck Mini project](https://github.com/apirrone/Open_Duck_Mini).

The upstream [CITATION.cff](https://github.com/TheRobotStudio/SO-ARM100/blob/eecbe3e0a9ebb23e25ad7b2759b03884c6660903/CITATION.cff) requests citation of *Standard Open SO-100 & SO-101 Arms* (2024) and lists Rob Knight, Pepijn Kooijmans, Remi Cadene, Simon Alibert, Michel Aractingi, Dana Aubakirova, Adil Zouitine, Russi Martino, Steven Palma, Caroline Pascal, and Thomas Wolf.

## Inter font

- File: `assets/fonts/InterVariable.ttf`, unmodified.
- Project: [Inter](https://github.com/rsms/inter).
- Pinned revision: `353b61b9f4430d5f420d56605a6e7993e0941470`.
- Copyright notice: `Copyright (c) 2016 The Inter Project Authors (https://github.com/rsms/inter)`.
- License: **SIL Open Font License, Version 1.1**, reproduced with its copyright notice in [assets/fonts/LICENSE.txt](assets/fonts/LICENSE.txt).
- Exact download URLs, modification status, and SHA-256 checksums are recorded in [assets/fonts/SOURCE.json](assets/fonts/SOURCE.json).

The font is included to reproduce the video captions. Its license permits bundling with software while requiring preservation of the font's license and copyright notice. The OFL's font-license requirement does not apply to documents or videos created using the font.

## Runtime and media-generation dependencies

MuJoCo, NumPy, OpenCV, Pillow, and any video-encoding tools used by this package are separate projects. Their own distributions and license notices govern those dependencies; the package's Apache license does not replace them. The pinned dependency manifest and lockfile describe the Python versions used for reproduction.

The example scene renders and video composition were produced for this package using the credited robot assets. References to upstream project names identify provenance and do not imply upstream endorsement of this modified simulation or its results.
