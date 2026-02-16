# CFU Counter - Product Specification

**Version:** 0.2 (Draft)
**Last Updated:** 2026-02-08
**Author:** Anirudh Desai

---

## 1. Vision

A web-based colony counting service that is faster, cheaper, and more accurate than existing solutions -- with transparent, verifiable results that anyone counting colonies can trust.

## 2. Who This Is For

Anyone who counts bacterial colonies on agar plates: food safety labs, pharma QC, academic researchers, clinical microbiology, water treatment, cosmetics testing. The product is domain-agnostic -- it counts colonies, period.

- **Pain today:** Manual counting is slow (1-3 min/plate), error-prone, and has no audit trail. Hardware counters ($5K-$30K) are accurate but expensive. Cheap web tools lack correction workflows and verifiable results.
- **What they need:** Upload a photo, get an accurate count with annotations, correct mistakes, export a report.

### Go-to-market (not a product constraint):

Initial marketing will target food safety QC labs (highest willingness to pay, clearest pain point), but the product itself makes no domain-specific assumptions.

## 3. Scope: Counting Only

The MVP counts **total colonies** on a plate. No species classification, no morphology analysis, no antibiotic susceptibility. One number, verified by the user.

**Why counting-only:**
- Simpler model (1 class: "colony"), higher accuracy, faster iteration
- Classification can be layered on later without changing the core UX

## 4. Competitive Landscape

| Competitor | Type | Price | Strengths | Weaknesses |
|---|---|---|---|---|
| Manual counting | Clicker + pen | Free | Trusted, no tech | Slow, error-prone, no audit trail |
| Fisher Scan 300/500 | Hardware + software | $5K-$15K | Fast, validated | Expensive, locked to one station |
| KEYENCE BC-1000 | Hardware + software | $15K-$30K | High precision | Very expensive, overkill for many labs |
| Neutec SphereFlash | Hardware + software | $3K-$10K | AI software, upgradeable | Still requires dedicated hardware |
| Reshape Biotech | Hardware + cloud | Enterprise pricing | 50M+ training images, LIMS integration | Enterprise-only, requires their imaging unit |
| online-colony-counter.com | Web app | ~$19/year | Cheap, accessible | No audit trail, no correction UI, low accuracy, no food-safety validation |
| OpenCFU | Desktop software | Free | Open source | Manual parameter tuning, no cloud, dated |
| BactLAB | Mobile app | Free | Quick phone photos | Only works with CompactDry media |

### Our positioning

**"Hardware-grade accuracy, software-only price."**

We sit between the cheap-but-unreliable web tools and the expensive-but-accurate hardware counters. We charge more than online-colony-counter.com but deliver verifiable, correctable results with audit-ready exports -- at a fraction of the cost of dedicated hardware.

## 5. Core User Flow

### Flow: Count colonies on a plate image

```
[1] Upload       [2] Processing     [3] Results        [4] Review         [5] Export

 Drop/snap       "Counting..."      Annotated plate    Zoom + correct     PDF/CSV
 plate image     (2-5 sec)          with count         add/remove/split   with audit trail
```

### Step-by-step:

**Step 1: Upload**
- Drag-and-drop or click to select an image
- Also: camera capture button for mobile (phone photo of plate)
- Accepts JPEG, PNG, TIFF
- Max file size: 25 MB
- No login required for first 5 free counts (conversion funnel)

**Step 2: Processing**
- Loading state with progress indicator
- Target: < 5 seconds for inference on a single image
- Backend runs RT-DETR detection, returns bounding boxes + confidence scores

**Step 3: Results**
- Full plate image displayed with overlay annotations
- Each detected colony marked with a small numbered dot/circle
- Total count displayed prominently (e.g., "247 colonies detected")
- Confidence summary (e.g., "High confidence" / "Review suggested" based on average detection confidence)

**Step 4: Review and Correct**
- **Zoom on hover/click:** Hovering over any region shows a magnified view with individual colony annotations clearly visible
- **Add colony:** Click on an unmarked colony to add it to the count
- **Remove false positive:** Click on a marked colony to remove it
- **Split merged detection:** Click on a large bounding box to split it into multiple colonies (common in dense regions)
- Count updates live as user makes corrections
- Correction count tracked (e.g., "+3 added, -1 removed" shown alongside final count)

**Step 5: Export**
- Generate PDF report containing:
  - Original image
  - Annotated image (with all corrections applied)
  - Total count (original model count + user corrections = final count)
  - Timestamp
  - Correction log (what was added/removed)
  - Operator name (if logged in)
- Also available: CSV with per-colony coordinates and confidence scores
- Also available: annotated image download (JPEG/PNG)

### Secondary flows:

**Batch upload (paid tier):**
- Upload multiple plate images at once (ZIP or multi-select)
- Processing queue with progress for each
- Results table with per-plate count + link to review each
- Batch CSV export

**History (logged-in users):**
- View past counts with images and reports
- Re-open any past count for re-review

## 6. Accuracy Requirements

### Target metrics:

| Metric | Target | Rationale |
|---|---|---|
| Count within 5% of ground truth | > 90% | Better than inter-operator manual variability (~10-15%) |
| Count exact match | > 70% | Matches or beats YOLOv8 baseline (69.5%) |
| False positive rate | < 2% | Users trust the count without excessive corrections |
| False negative rate | < 5% | Missing colonies is worse than overcounting |

### Density range: sparse to dense

The model must handle the full range of colony densities:
- **Sparse plates** (< 25 colonies): Easy for humans but still useful for speed and audit trail
- **Standard range** (25-250): The industry "countable" range. Must be excellent here.
- **Dense plates** (250-1000+): Where humans give up and report TNTC. This is our differentiator -- accurate counting where manual counting fails.

Industry context: FDA BAM Chapter 3 defines 25-250 as the countable range. Above 250, plates are traditionally reported as TNTC (Too Numerous To Count). A tool that can reliably count into the hundreds is immediately more useful than manual counting.

### What "beats competitors" means:

- vs. manual counting: Faster (seconds vs minutes) + audit trail + reproducible + counts beyond TNTC
- vs. cheap web tools: Correction UI + audit export + validated accuracy numbers
- vs. hardware counters: 90%+ of the accuracy at 1% of the price

### Accuracy validation strategy:

- Publish accuracy metrics on the website (transparency builds trust)
- Benchmark on a held-out test set across density ranges
- Allow users to report "bad counts" to improve the model over time

## 7. Technical Decisions

### Model: Single-class detection

- Retrain RT-DETR with all 7 AGAR classes merged into 1 class ("colony")
- This should improve accuracy: the model only needs to find "round blob" not distinguish species
- Evaluate if a simpler architecture (smaller RT-DETR variant) is sufficient for 1-class detection
- Inference target: < 3 seconds on GPU, < 10 seconds on CPU fallback

### Image handling:

- Accept any reasonable plate photo (phone camera, flatbed scanner, colony counter camera)
- Auto-detect plate boundary (circular crop) to focus detection on the agar surface
- Handle common issues: partial plate, glare, uneven lighting, tilted angle

### Infrastructure:

- Existing FastAPI + React stack is the right foundation
- GPU inference via RunPod serverless or similar (pay-per-inference)
- Image storage in MinIO/S3 (already built)

## 8. What We Are NOT Building (at launch)

- Species classification or morphology analysis
- LIMS integration
- 21 CFR Part 11 / GxP compliance features
- API access for programmatic use
- Custom model training per customer
- Hardware imaging devices
- Mobile native app (web-only, responsive)

## 9. Success Metrics (first 3 months post-launch)

| Metric | Target |
|---|---|
| Free sign-ups | 200+ |
| Free-to-paid conversion | 5-10% |
| Plates counted per paid user per month | 50+ |
| User-reported "bad count" rate | < 10% of plates |
| Average corrections per plate | < 5% of total count |

## 10. Pricing (TBD - placeholder)

Pricing to be determined after competitive analysis and user interviews. Working assumptions:

- **Free tier:** 5-10 counts/month, no export, no history
- **Pro tier:** Unlimited counts, batch upload, PDF/CSV export, history -- $29-49/month
- **Team tier:** Multiple operators, shared history, admin dashboard -- $99-149/month

Price must be low enough that a lab manager can expense it without procurement approval (typically < $100/month), but high enough to signal quality vs. the $19/year competitor.

## 11. Resolved Questions

1. **Image quality:** Any modern smartphone camera (iPhone or Android, 12MP+) produces images at or above the resolution of our training data (AGAR dataset: 4000x6000px and 2048x2048px). Flatbed scanners and dedicated colony counter cameras also work. No minimum resolution gate needed at launch -- if the image is too poor, the model will simply produce low-confidence detections and the user will see that.

2. **Plate type support at launch:** The AGAR dataset uses TSA (Trypticase Soy Agar) plates exclusively. At launch, we validate and claim accuracy on TSA. The model may generalize to other media (PCA, nutrient agar) since colony morphology is similar, but we make no claims until validated. Selective/differential media (MacConkey, blood agar, chromogenic) look very different and will need separate validation or fine-tuning data.

3. **Count range:** The standard countable range is 25-250 colonies per plate (FDA BAM Chapter 3). Above 250 is traditionally TNTC. Our model targets the full range including dense plates (250-1000+) as a differentiator. See Section 6.

4. **Regulatory:** No specific FDA certification or approval is required for colony counting software. Labs operate under ISO/IEC 17025 (lab accreditation) and FDA FSMA, but those regulate the lab's processes, not the counting tool. What matters is audit trail and traceability -- our PDF export with correction log serves this need. Pharma-grade compliance (21 CFR Part 11) is out of scope for launch.

5. **Data collection:** Yes, we want to use anonymized user-uploaded images (with explicit consent) to continuously improve the model. Implementation deferred to post-launch.

6. **Single-class accuracy:** Need to benchmark single-class RT-DETR vs. 7-class to confirm accuracy improvement hypothesis. Deferred to model development phase.
