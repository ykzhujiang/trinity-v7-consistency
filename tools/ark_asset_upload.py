#!/usr/bin/env python3 -u
"""
ark_asset_upload.py — Upload images to Volcano Engine private trusted asset library.

Returns asset://asset-xxx IDs for Seedance 2.0 video generation.

Usage:
  # Single image
  python3 -u tools/ark_asset_upload.py --image /path/to/img.png --group-name "exp-v7-040"

  # Multiple images  
  python3 -u tools/ark_asset_upload.py --images img1.png img2.png --group-name "exp-v7-040" --names "char" "scene"

  # Reuse existing group
  python3 -u tools/ark_asset_upload.py --image img.png --group-id group-xxx

  # Image already at URL
  python3 -u tools/ark_asset_upload.py --image-url https://example.com/img.png --group-name "test"

Auth: VOLCANO_ACCESS_KEY / VOLCANO_ACCESS_SECRET env vars (or pass --ak/--sk).
"""

import argparse
import datetime
import hashlib
import hmac
import json
import os
import subprocess
import sys
import time
import urllib.parse
import urllib.request

# ── Volcengine V4 Signature ──────────────────────────────────────────────────

SERVICE = "ark"
REGION = "cn-beijing"
API_VERSION = "2024-01-01"
HOST = "open.volcengineapi.com"


def _sign(key: bytes, msg: str) -> bytes:
    return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()


def _get_signature_key(secret: str, date_stamp: str, region: str, service: str) -> bytes:
    k_date = _sign(secret.encode("utf-8"), date_stamp)
    k_region = _sign(k_date, region)
    k_service = _sign(k_region, service)
    k_signing = _sign(k_service, "request")
    return k_signing


def volcengine_request(action: str, body: dict, ak: str, sk: str) -> dict:
    """Make a signed POST request to Volcengine API."""
    now = datetime.datetime.utcnow()
    date_stamp = now.strftime("%Y%m%d")
    amz_date = now.strftime("%Y%m%dT%H%M%SZ")

    # Query params
    query_params = {
        "Action": action,
        "Version": API_VERSION,
    }
    canonical_querystring = urllib.parse.urlencode(sorted(query_params.items()))

    payload = json.dumps(body)
    payload_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()

    headers_to_sign = {
        "content-type": "application/json",
        "host": HOST,
        "x-date": amz_date,
        "x-content-sha256": payload_hash,
    }
    signed_headers = ";".join(sorted(headers_to_sign.keys()))
    canonical_headers = "".join(
        f"{k}:{v}\n" for k, v in sorted(headers_to_sign.items())
    )

    canonical_request = "\n".join([
        "POST",
        "/",
        canonical_querystring,
        canonical_headers,
        signed_headers,
        payload_hash,
    ])

    credential_scope = f"{date_stamp}/{REGION}/{SERVICE}/request"
    string_to_sign = "\n".join([
        "HMAC-SHA256",
        amz_date,
        credential_scope,
        hashlib.sha256(canonical_request.encode("utf-8")).hexdigest(),
    ])

    signing_key = _get_signature_key(sk, date_stamp, REGION, SERVICE)
    signature = hmac.new(signing_key, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()

    authorization = (
        f"HMAC-SHA256 Credential={ak}/{credential_scope}, "
        f"SignedHeaders={signed_headers}, Signature={signature}"
    )

    url = f"https://{HOST}/?{canonical_querystring}"
    req = urllib.request.Request(
        url,
        data=payload.encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Host": HOST,
            "X-Date": amz_date,
            "X-Content-Sha256": payload_hash,
            "Authorization": authorization,
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="replace")
        print(f"[ERROR] {action} HTTP {e.code}: {error_body}", file=sys.stderr)
        raise
    except Exception as e:
        print(f"[ERROR] {action}: {e}", file=sys.stderr)
        raise

    # Check for API-level error
    meta = data.get("ResponseMetadata", {})
    if "Error" in meta:
        err = meta["Error"]
        raise RuntimeError(f"{action} API error: {err.get('Code', '?')} — {err.get('Message', '?')}")

    return data


# ── Asset Operations ─────────────────────────────────────────────────────────

def create_asset_group(name: str, description: str, ak: str, sk: str, project: str = "default") -> str:
    """Create an asset group. Returns group ID."""
    body = {
        "Name": name,
        "Description": description,
        "GroupType": "AIGC",
    }
    if project != "default":
        body["ProjectName"] = project

    print(f"[INFO] Creating asset group: {name}", file=sys.stderr)
    resp = volcengine_request("CreateAssetGroup", body, ak, sk)
    result = resp.get("Result", resp)
    group_id = result.get("Id", "")
    if not group_id:
        raise RuntimeError(f"CreateAssetGroup returned no Id: {resp}")
    print(f"[INFO] Group created: {group_id}", file=sys.stderr)
    return group_id


def create_asset(group_id: str, url: str, name: str, ak: str, sk: str, project: str = "default") -> str:
    """Upload an asset. Returns asset ID."""
    body = {
        "GroupId": group_id,
        "URL": url,
        "AssetType": "Image",
    }
    if name:
        body["Name"] = name
    if project != "default":
        body["ProjectName"] = project

    print(f"[INFO] Creating asset from URL: {url[:80]}...", file=sys.stderr)
    resp = volcengine_request("CreateAsset", body, ak, sk)
    result = resp.get("Result", resp)
    asset_id = result.get("Id", "")
    if not asset_id:
        raise RuntimeError(f"CreateAsset returned no Id: {resp}")
    print(f"[INFO] Asset created: {asset_id} (processing...)", file=sys.stderr)
    return asset_id


def wait_for_active(asset_id: str, ak: str, sk: str, timeout: int = 120, project: str = "default") -> str:
    """Poll GetAsset until Active/Failed/timeout. Returns asset_id on success."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        body = {"Id": asset_id}
        if project != "default":
            body["ProjectName"] = project

        resp = volcengine_request("GetAsset", body, ak, sk)
        result = resp.get("Result", resp)
        status = result.get("Status", "")

        if status == "Active":
            print(f"[INFO] Asset {asset_id} is Active", file=sys.stderr)
            return asset_id
        elif status == "Failed":
            error = result.get("Error", {})
            raise RuntimeError(f"Asset {asset_id} failed: {error}")
        else:
            print(f"[INFO] Asset {asset_id} status: {status}, waiting...", file=sys.stderr)
            time.sleep(3)

    raise TimeoutError(f"Asset {asset_id} did not become Active within {timeout}s")


# ── Image URL Hosting ────────────────────────────────────────────────────────

def make_image_public(image_path: str, repo_dir: str = None) -> str:
    """Make a local image publicly accessible via GitHub raw URL."""
    if image_path.startswith("http://") or image_path.startswith("https://"):
        return image_path

    if not os.path.isfile(image_path):
        raise FileNotFoundError(f"Image not found: {image_path}")

    # Default repo
    if repo_dir is None:
        repo_dir = os.path.expanduser("~/trinity-v3-content")

    if not os.path.isdir(repo_dir):
        raise RuntimeError(f"GitHub repo not found at {repo_dir}. Use --image-url for pre-hosted images.")

    # Copy to repo's asset-uploads/ directory
    upload_dir = os.path.join(repo_dir, "asset-uploads")
    os.makedirs(upload_dir, exist_ok=True)

    basename = os.path.basename(image_path)
    # Add timestamp to avoid collisions
    ts = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    dest_name = f"{ts}-{basename}"
    dest_path = os.path.join(upload_dir, dest_name)

    # Copy file
    import shutil
    shutil.copy2(image_path, dest_path)

    # Git add + commit + push
    print(f"[INFO] Uploading {basename} to GitHub for public URL...", file=sys.stderr)
    cmds = [
        ["git", "add", f"asset-uploads/{dest_name}"],
        ["git", "commit", "-m", f"[operator] asset upload: {dest_name}"],
        ["git", "pull", "--rebase", "origin", "main"],
        ["git", "push", "origin", "main"],
    ]
    for cmd in cmds:
        r = subprocess.run(cmd, cwd=repo_dir, capture_output=True, text=True, timeout=60)
        if r.returncode != 0:
            print(f"[WARN] {' '.join(cmd)}: {r.stderr.strip()}", file=sys.stderr)
            # commit might fail if nothing to commit, that's ok for add
            if cmd[1] not in ("add",):
                # push failure is fatal
                if cmd[1] == "push":
                    raise RuntimeError(f"git push failed: {r.stderr}")

    # Construct raw URL
    # Detect GitHub user/repo from remote
    r = subprocess.run(["git", "remote", "get-url", "origin"], cwd=repo_dir, capture_output=True, text=True)
    remote_url = r.stdout.strip()
    # Parse: git@github.com:user/repo.git or https://github.com/user/repo.git
    if "github.com:" in remote_url:
        parts = remote_url.split("github.com:")[1].replace(".git", "").split("/")
    elif "github.com/" in remote_url:
        parts = remote_url.split("github.com/")[1].replace(".git", "").split("/")
    else:
        raise RuntimeError(f"Cannot parse GitHub remote: {remote_url}")

    user, repo = parts[0], parts[1]
    raw_url = f"https://raw.githubusercontent.com/{user}/{repo}/main/asset-uploads/{dest_name}"

    # Wait a moment for GitHub to propagate
    print(f"[INFO] Public URL: {raw_url}", file=sys.stderr)
    time.sleep(2)
    return raw_url


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Upload images to Volcano Engine private trusted asset library",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Single local image
  %(prog)s --image char.png --group-name "exp-v7-040"

  # Multiple images
  %(prog)s --images char.png scene.png --group-name "exp-v7-040" --names "char-lilei" "scene-office"

  # Image already at URL
  %(prog)s --image-url https://example.com/img.png --group-name "test"

  # Reuse existing group
  %(prog)s --image char.png --group-id group-xxx
        """,
    )

    # Image source (mutually exclusive)
    img_group = parser.add_mutually_exclusive_group(required=True)
    img_group.add_argument("--image", help="Local image file path")
    img_group.add_argument("--images", nargs="+", help="Multiple local image files")
    img_group.add_argument("--image-url", help="Image URL (already public)")
    img_group.add_argument("--image-urls", nargs="+", help="Multiple image URLs")

    # Group
    grp = parser.add_mutually_exclusive_group(required=True)
    grp.add_argument("--group-name", help="Create new group with this name")
    grp.add_argument("--group-id", help="Use existing group ID")

    # Optional
    parser.add_argument("--name", help="Asset name (single image)")
    parser.add_argument("--names", nargs="+", help="Asset names (batch)")
    parser.add_argument("--project", default="default", help="Project name (default: default)")
    parser.add_argument("--timeout", type=int, default=120, help="Polling timeout seconds (default: 120)")
    parser.add_argument("--repo-dir", help="GitHub repo for hosting local images")
    parser.add_argument("--ak", help="Access Key (default: env VOLCANO_ACCESS_KEY)")
    parser.add_argument("--sk", help="Secret Key (default: env VOLCANO_ACCESS_SECRET)")
    parser.add_argument("--json", action="store_true", help="Output JSON instead of plain asset:// lines")

    args = parser.parse_args()

    # Auth
    ak = args.ak or os.environ.get("VOLCANO_ACCESS_KEY", "")
    sk = args.sk or os.environ.get("VOLCANO_ACCESS_SECRET", "")
    if not ak or not sk:
        print("[ERROR] VOLCANO_ACCESS_KEY and VOLCANO_ACCESS_SECRET required", file=sys.stderr)
        sys.exit(1)

    # Collect image sources
    image_sources = []  # list of (path_or_url, name)
    if args.image:
        image_sources.append((args.image, args.name or ""))
    elif args.images:
        names = args.names or [""] * len(args.images)
        if len(names) < len(args.images):
            names.extend([""] * (len(args.images) - len(names)))
        image_sources = list(zip(args.images, names))
    elif args.image_url:
        image_sources.append((args.image_url, args.name or ""))
    elif args.image_urls:
        names = args.names or [""] * len(args.image_urls)
        if len(names) < len(args.image_urls):
            names.extend([""] * (len(args.image_urls) - len(names)))
        image_sources = list(zip(args.image_urls, names))

    if not image_sources:
        print("[ERROR] No images specified", file=sys.stderr)
        sys.exit(1)

    # Group
    if args.group_id:
        group_id = args.group_id
    else:
        group_id = create_asset_group(args.group_name, f"Auto-created for {args.group_name}", ak, sk, args.project)

    # Upload each image
    results = []
    for src, name in image_sources:
        try:
            # Make URL public if local file
            if src.startswith("http://") or src.startswith("https://"):
                url = src
            else:
                url = make_image_public(src, args.repo_dir)

            # Create asset
            asset_id = create_asset(group_id, url, name, ak, sk, args.project)

            # Wait for active
            asset_id = wait_for_active(asset_id, ak, sk, args.timeout, args.project)

            asset_uri = f"asset://{asset_id}"
            results.append({"asset_uri": asset_uri, "asset_id": asset_id, "name": name, "source": src, "status": "ok"})
            print(f"[OK] {name or src}: {asset_uri}", file=sys.stderr)

        except Exception as e:
            results.append({"asset_uri": None, "name": name, "source": src, "status": "error", "error": str(e)})
            print(f"[ERROR] {name or src}: {e}", file=sys.stderr)

    # Output
    if args.json:
        output = {"group_id": group_id, "assets": results}
        print(json.dumps(output, indent=2))
    else:
        for r in results:
            if r["asset_uri"]:
                print(r["asset_uri"])
            else:
                print(f"ERROR: {r['error']}", file=sys.stderr)

    # Exit code
    if any(r["status"] == "error" for r in results):
        sys.exit(1)


if __name__ == "__main__":
    main()
