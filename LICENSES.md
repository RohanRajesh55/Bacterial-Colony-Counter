# Third-Party Licenses and Compliance

This document tracks license obligations for all significant dependencies and datasets used in the CFU-Counter project. It establishes the separation between research and commercial tracks to ensure license compliance.

## Quick Reference

| Track | License Requirements | Key Restrictions |
|-------|---------------------|------------------|
| **Research** | AGPL-3.0 (YOLO), CC BY-NC 2.0 (AGAR) | Internal use only, no production deployment |
| **Commercial** | Apache 2.0, MIT, BSD | Attribution required, production-safe |

---

## Track Separation Policy

### Research Track (Internal Only)

The research track is for internal experimentation, benchmarking, and model development. Code and models from this track **MUST NOT** be deployed to production or made accessible over a network.

**Components:**
- Ultralytics YOLO models (`ultralytics` package)
- Models trained on AGAR dataset
- Any code importing from `ultralytics`

**Allowed uses:**
- Local experimentation and training
- Internal benchmarking and comparison
- Research paper results
- Informing commercial track architecture decisions

**Prohibited uses:**
- Production API endpoints
- User-facing inference
- Network-accessible services
- Distribution without open-sourcing entire application

### Commercial Track (Production)

The commercial track contains only permissively-licensed components safe for SaaS deployment.

**Components:**
- RT-DETR model (Apache 2.0)
- PyTorch, FastAPI, and standard stack
- Models trained on commercially-licensed datasets only

**Allowed uses:**
- Production API deployment
- User-facing inference
- Commercial SaaS operation
- Proprietary modifications

---

## Model Licenses

### Ultralytics YOLO (Research Track Only)

**License:** AGPL-3.0 (GNU Affero General Public License v3.0)

**Source:** https://github.com/ultralytics/ultralytics

**License URL:** https://www.ultralytics.com/license

**Key obligations:**
- Any derivative work must be released under AGPL-3.0
- Network use (SaaS) triggers the same obligations as distribution
- Must provide complete source code to users accessing the service
- Cannot be used in proprietary commercial products without Enterprise License

**Our approach:**
- YOLO is restricted to the research track only
- No production code may import `ultralytics`
- YOLO benchmarks inform architecture decisions but are not deployed

**Enterprise alternative:** Ultralytics offers commercial licenses. Contact: https://www.ultralytics.com/license

### RT-DETR (Commercial Track)

**License:** Apache 2.0

**Source:** https://github.com/lyuwenyu/RT-DETR

**License URL:** https://github.com/lyuwenyu/RT-DETR/blob/main/LICENSE

**Key obligations:**
- Include copyright notice and license text
- State changes if modified
- No trademark use without permission

**Our approach:**
- RT-DETR is the production model architecture
- Apache 2.0 allows proprietary modifications
- Full commercial use permitted

**IMPORTANT - Model Weights Distinction:**

| Weight Source | License | Commercial Use |
|---------------|---------|----------------|
| Pre-trained (HuggingFace) | Apache 2.0 | Yes |
| Fine-tuned on AGAR | CC BY-NC 2.0 | NO - Research only |
| Fine-tuned on CC BY 4.0 data | Apache 2.0 + CC BY 4.0 | Yes |

The RT-DETR architecture (code) is Apache 2.0, but model weights inherit the license of their training data. AGAR-trained weights are research-only.

---

## Dataset Licenses

### AGAR Dataset (Research Track Only)

**License:** CC BY-NC 2.0 (Creative Commons Attribution-NonCommercial 2.0)

**Source:** https://agar.neurosys.com/

**Citation:** Majchrowska et al., "AGAR a microbial colony dataset for deep learning detection"

**Key restrictions:**
- **NonCommercial:** Cannot be used for commercial model training
- Attribution required in any use

**Our approach:**
- AGAR used for research track experiments only
- Production models must be trained on commercially-licensed data
- Cannot use AGAR-trained model weights in production

### Alternative Datasets for Commercial Track

For the commercial track, models must be trained on data with commercial-friendly licenses:

- **Self-collected data:** Owned, no license restrictions
- **CC BY 4.0 datasets:** Commercial use permitted with attribution
- **Licensed datasets:** Purchased or licensed for commercial use

---

## Core Dependencies

### Production-Safe (Commercial Track)

| Package | License | Usage |
|---------|---------|-------|
| PyTorch | BSD-3-Clause | Deep learning framework |
| FastAPI | MIT | API framework |
| Pydantic | MIT | Data validation |
| OpenCV (opencv-python) | Apache 2.0 | Image processing |
| NumPy | BSD-3-Clause | Numerical computing |
| Pillow | HPND | Image I/O |
| albumentations | MIT | Image augmentation |
| scikit-learn | BSD-3-Clause | ML utilities |
| pandas | BSD-3-Clause | Data manipulation |
| tqdm | MIT/MPL-2.0 | Progress bars |

All packages above are permissive licenses compatible with proprietary commercial use.

### Research-Only Dependencies

| Package | License | Restriction |
|---------|---------|-------------|
| ultralytics | AGPL-3.0 | Research track only |

---

## Directory Structure by Track

```
CFU-Counter/
    yolo/                    # RESEARCH TRACK - Uses ultralytics (AGPL-3.0)
        yolov8_train.py      # Research only
        yolov8_test.py       # Research only
        data.yaml            # Research only

    cnn/                     # RESEARCH TRACK - Can be adapted for commercial
        cnn_train.py         # Uses PyTorch only (BSD)
        cnn_test.py          # Uses PyTorch only (BSD)

    rtdetr_v2/               # MIXED TRACK - Training code is Apache 2.0
        train.py             # Training script (Apache 2.0)
        test.py              # Evaluation script (Apache 2.0)
        dataset.py           # Dataset loader (Apache 2.0)
        config.yaml          # Configuration (Apache 2.0)
        checkpoints/         # RESEARCH ONLY if trained on AGAR (CC BY-NC 2.0)

    rtdetr_v4/               # MIXED TRACK - Official RT-DETRv4 (Apache 2.0)
        configs/             # Model configs (Apache 2.0)
        engine/              # Training engine (Apache 2.0)
        tools/               # Utilities (Apache 2.0)
        train.py             # Training script (Apache 2.0)

    api/                     # COMMERCIAL TRACK
        ...                  # RT-DETR inference, no ultralytics imports

    frontend/                # COMMERCIAL TRACK
        ...                  # React (MIT)
```

**Note on rtdetr_v2/ and rtdetr_v4/ directories:**
- The training code itself (train.py, dataset.py, etc.) is Apache 2.0 licensed
- Model checkpoints in `rtdetr_v2/checkpoints/` or `rtdetr_v4/output/` inherit the license of their training data:
  - AGAR-trained: Research only (CC BY-NC 2.0)
  - CC BY 4.0 dataset-trained: Commercial use allowed

---

## Compliance Checklist

Before any production deployment, verify:

- [ ] No `from ultralytics import` in production code paths
- [ ] No YOLO model weights (.pt files from ultralytics training) in production
- [ ] Production models trained only on commercially-licensed data
- [ ] RT-DETR or other Apache 2.0 architecture used for inference
- [ ] Attribution notices included for all Apache 2.0 / MIT dependencies
- [ ] AGAR-trained RT-DETR weights NOT deployed to production
- [ ] Only CC BY 4.0 (or similar) trained weights used in production API

**RT-DETR Model Checkpoint Verification:**
```bash
# Check if a checkpoint was trained on AGAR (research only)
# Look for "AGAR" or "research" in the training config
python -c "import torch; c = torch.load('checkpoint.pt'); print(c.get('config', {}))"
```

---

## License Text References

- **AGPL-3.0:** https://www.gnu.org/licenses/agpl-3.0.en.html
- **Apache 2.0:** https://www.apache.org/licenses/LICENSE-2.0
- **CC BY-NC 2.0:** https://creativecommons.org/licenses/by-nc/2.0/
- **BSD-3-Clause:** https://opensource.org/licenses/BSD-3-Clause
- **MIT:** https://opensource.org/licenses/MIT

---

*Last updated: 2026-01-26*
*Review schedule: Before each production release*
