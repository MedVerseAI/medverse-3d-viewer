# medverse-3d-viewer

Standalone web-based 3D viewer and interactive quiz for exploring anatomical models produced by the **MedVerse Asset Ingestion** pipeline (`medverse-asset-ingestion`). Supports desktop and mobile browsers independently of the Unity VR client and professor web dashboard.

## Quick Start

1. Download the latest decimated Draco-compressed `anatomical_model_quest3_lod0.glb` from the [`MedVerseAI/medverse-asset-ingestion` Releases](https://github.com/MedVerseAI/medverse-asset-ingestion/releases) page (or build one directly with `medverse run --profile quest3_lod0`) and save it as `atlasview_quiz/web/model.glb`.
2. Serve locally or via Docker:

```bash
cd atlasview_quiz
python3 -m http.server 8080 --directory web
# Or build and run the Nginx container:
docker compose up -d --build
```

3. Open `http://localhost:8080`.

> Multi-MB `.glb` / `.blend` binaries are intentionally git-ignored and distributed via GitHub Releases / Git LFS rather than committed directly into Git history.

---

## Data Attribution & Licensing

- **Viewer Source Code:** Licensed under the **MIT License** (see [`LICENSE`](LICENSE)). The MIT license applies strictly to this repository's web viewer, quiz, Docker, and helper scripts—**not** to third-party anatomical atlas data or derived 3D meshes (`model.glb`).
- **BodyParts3D v4.0 (DBCLS):** Derived spinal, brainstem, cerebellar, ventricular, white-matter, and deep anatomical meshes originate from **BodyParts3D**, © The Database Center for Life Science (DBCLS), licensed under **[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)** (attribution required; source: `https://dbarchive.biosciencedbc.jp/en/bodyparts3d/`).
- **Human Brainnetome Atlas (CASIA):** Derived 246-region cortical and subcortical brain parcellations originate from the **Human Brainnetome Atlas**, Brainnetome Center, Institute of Automation, Chinese Academy of Sciences (CASIA), licensed for **non-commercial research and educational use (share-alike, attribution required)** (`https://atlas.brainnetome.org/`). Mandatory citation:
  > Fan L., Li H., Zhuo J., Zhang Y., Wang J., Chen L., Yang Z., Chu C., Xie S., Laird A.R., Fox P.T., Eickhoff S.B., Yu C., Jiang T. (2016). *The Human Brainnetome Atlas: A New Brain Atlas Based on Connectional Architecture.* **Cerebral Cortex**, 26(8): 3508–3526.
- **Educational & Non-Clinical Notice:** Intended exclusively for education, anatomical visualization, and research—not for clinical diagnosis or surgical guidance.
