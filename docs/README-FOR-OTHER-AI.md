# Instructions for Other AI - Low Confidence Fix

## Quick Summary
The detector "Vehicle Detection Lot A" (`2467f56e-07bb-447e-9122-47595563e34a`) returns very low confidence scores (3-8%) even though detections are correct. This is because the OODD (out-of-domain detection) model thinks parking lot images are "weird" and crushes the confidence scores.

**Fix**: Disable OODD model for this detector.

## What to Read (In Order)

### 1. Understanding the Problem
**Read**: `LOW-CONFIDENCE-ISSUE-ANALYSIS.md`
- Explains root cause (OODD model mismatch)
- Shows evidence from logs
- Lists solution options
- Provides long-term roadmap

### 2. Implementing the Fix
**Read**: `QUICK-FIX-OODD-DISABLE.md`
- Step-by-step commands (copy-paste ready)
- Verification checklist
- Rollback procedure
- Troubleshooting guide

### 3. Understanding Previous Work (Context)
**Read**: `DETECTOR-MODEL-PATH-FIX.md`
- How we fixed the "model not found" error
- Worker cache management procedures
- Model path configuration

## One-Command Summary

If you only want to fix it NOW without reading everything:

```bash
cd "C:\Dev\IntelliOptics 2.0\cloud"

# Backup
docker-compose exec postgres psql -U intellioptics -d intellioptics -c "SELECT id, name, primary_model_blob_path, oodd_model_blob_path FROM detectors WHERE id = '2467f56e-07bb-447e-9122-47595563e34a';" > backup.txt

# Disable OODD
docker-compose exec postgres psql -U intellioptics -d intellioptics -c "UPDATE detectors SET oodd_model_blob_path = NULL WHERE id = '2467f56e-07bb-447e-9122-47595563e34a';"

# Clear cache & restart
docker-compose stop worker
docker-compose run --rm worker sh -c "rm -rf /app/models/2467f56e-07bb-447e-9122-47595563e34a"
docker-compose start worker

# Wait 5 seconds for worker to start
sleep 5

# Test via UI: http://localhost → Detectors → Vehicle Detection Lot A → Upload image → Run Test
# Expected: Confidence 50-90% (not 3-8%)
```

## What Changed in the System

### Before Our Fixes
- ❌ Model paths pointed to non-existent detector-specific folders
- ❌ Worker cache had corrupted model files
- ❌ "Model not found" errors
- ❌ Couldn't run inference at all

### After Model Path Fix (Previous Session)
- ✅ Database paths updated to global models
- ✅ Worker cache cleared
- ✅ Inference works
- ❌ But confidence scores only 3-8% (too low)

### After OODD Disable (This Session - What You Need to Do)
- ✅ OODD model disabled for this detector
- ✅ Confidence scores normal (50-90%)
- ✅ System production-ready

## CRITICAL: What NOT to Touch

### ⚠️ DO NOT Change These
1. **Other detectors** - Only modify `2467f56e-07bb-447e-9122-47595563e34a`
2. **Database tables**: `queries`, `escalations`, `feedback` - Read-only
3. **Global models**: `/app/models/intellioptics-yolov10n.onnx` - Used by other detectors
4. **Cache for other detectors**: `/app/models/e1709250-*`, `/app/models/5e1bcea3-*`
5. **Worker inference code**: `detector_inference.py` - No code changes needed

### ✅ SAFE to Change
1. **This detector's database row** - `WHERE id = '2467f56e-07bb-447e-9122-47595563e34a'`
2. **This detector's cache** - `/app/models/2467f56e-07bb-447e-9122-47595563e34a/`
3. **Worker restarts** - Safe to restart worker service

## File Locations

```
C:\Dev\IntelliOptics 2.0\
├── docs\
│   ├── README-FOR-OTHER-AI.md (this file - start here)
│   ├── QUICK-FIX-OODD-DISABLE.md (step-by-step commands)
│   ├── LOW-CONFIDENCE-ISSUE-ANALYSIS.md (detailed analysis)
│   └── DETECTOR-MODEL-PATH-FIX.md (previous fix reference)
├── cloud\
│   ├── docker-compose.yml
│   ├── backend\
│   ├── frontend\
│   └── worker\
│       └── detector_inference.py (inference logic - no changes needed)
└── (database inside postgres container)
```

## Testing After Fix

### Test 1: Basic Functionality
```bash
# Should show NULL for oodd_model_blob_path
docker-compose exec postgres psql -U intellioptics -d intellioptics -c "SELECT id, name, primary_model_blob_path, oodd_model_blob_path FROM detectors WHERE id = '2467f56e-07bb-447e-9122-47595563e34a';"
```

### Test 2: Inference Results
1. Open browser: http://localhost (or your frontend URL)
2. Go to: Detectors → Vehicle Detection Lot A
3. Upload: Any image with vehicles (parking lot, street, etc.)
4. Click: "Run Test"
5. **Expected**: Confidence 50-90%, not 3-8%

### Test 3: Worker Logs
```bash
# Should NOT see OODD loading for this detector
docker-compose logs worker --tail=50 | grep -i "2467f56e"
```

**Good log**: "Loading Primary model for detector 2467f56e" (no mention of OODD)
**Bad log**: "Loading OODD model for detector 2467f56e" (OODD still enabled)

### Test 4: Other Detectors Unaffected
```bash
# Should show OODD paths for other detectors (unchanged)
docker-compose exec postgres psql -U intellioptics -d intellioptics -c "SELECT id, name, oodd_model_blob_path FROM detectors ORDER BY name;"
```

## Expected Timeline

- **Reading docs**: 10-15 minutes
- **Implementing fix**: 5 minutes
- **Testing**: 5 minutes
- **Total**: ~25 minutes

## Rollback

If something breaks, restore OODD:
```bash
docker-compose exec postgres psql -U intellioptics -d intellioptics -c "UPDATE detectors SET oodd_model_blob_path = 'models/ood_resnet18/resnet18-v1-7.onnx' WHERE id = '2467f56e-07bb-447e-9122-47595563e34a';"
docker-compose restart worker
```

## Questions to Ask User If Unclear

1. **"Do you have a test image I can use?"** - Helps verify fix immediately
2. **"Should I disable OODD for other detectors too?"** - If they have similar issues
3. **"Do you want me to train a custom OODD model?"** - Long-term fix (4+ hours)

## Success Criteria

You know you're done when:
1. ✅ Detector inference returns 50-90% confidence
2. ✅ Worker logs show no OODD loading for this detector
3. ✅ Database has NULL oodd_model_blob_path for this detector
4. ✅ Other detectors still work
5. ✅ User confirms confidence scores are normal

## Contact Previous AI (Me)

If you need clarification on:
- Why OODD causes low confidence
- How the inference pipeline works
- What each model does
- Cache management details

Refer back to the detailed analysis in `LOW-CONFIDENCE-ISSUE-ANALYSIS.md`.

## Final Note

This is a **quick fix** that disables a feature. The proper solution is to train a detector-specific OODD model (Phase 2 in the analysis document). But for now, disabling OODD makes the system functional and production-ready.

Good luck! 🚀

---
**Created**: 2026-01-13
**Context**: Detector 2467f56e-07bb-447e-9122-47595563e34a returning 3-8% confidence due to OODD domain mismatch
**Solution**: Disable OODD model, restore to Primary-only inference
