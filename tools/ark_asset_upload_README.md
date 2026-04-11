# ark_asset_upload.py

Upload images to Volcano Engine's private trusted asset library (火山引擎私域可信素材库) for Seedance 2.0 video generation.

## Usage

```bash
# Single image (already at public URL)
python3 -u tools/ark_asset_upload.py --image-url https://example.com/char.png --group-name "exp-v7-040"

# Single local image (auto-uploads to GitHub for public URL)
python3 -u tools/ark_asset_upload.py --image /path/to/char.png --group-name "exp-v7-040"

# Multiple images
python3 -u tools/ark_asset_upload.py --image-urls URL1 URL2 --group-name "exp-v7-040" --names "char" "scene"

# Reuse existing group
python3 -u tools/ark_asset_upload.py --image-url URL --group-id group-xxx

# JSON output
python3 -u tools/ark_asset_upload.py --image-url URL --group-name "test" --json
```

## Output

Prints `asset://asset-xxx` URIs to stdout (one per image). These can be passed directly to `seedance_gen.py --image asset://asset-xxx`.

## Auth

Requires `VOLCANO_ACCESS_KEY` and `VOLCANO_ACCESS_SECRET` environment variables (or `--ak`/`--sk` flags).

## API Flow

1. `CreateAssetGroup` — create a group (or reuse with `--group-id`)
2. `CreateAsset` — upload image via public URL
3. `GetAsset` polling — wait until status = Active (3s intervals, 120s timeout)
4. Return `asset://<asset_id>`

## Dependencies

Python 3.10+ stdlib only (no pip packages needed).
