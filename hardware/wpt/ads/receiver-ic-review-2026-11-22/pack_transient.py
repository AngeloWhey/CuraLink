"""Archive the startup dataset losslessly with a verified, portable SHA-256."""
from pathlib import Path
import argparse
import gzip
import hashlib
import json
import os
import shutil

HERE=Path(__file__).resolve().parent/"bridge-runs"/"startup"


def digest(file):
    h=hashlib.sha256()
    count=0
    for block in iter(lambda:file.read(1024*1024),b""):
        h.update(block)
        count+=len(block)
    return count,h.hexdigest()


def archive():
    ds=HERE/"startup.ds"
    target=HERE/"startup.ds.gz"
    tmp=HERE/"startup.ds.gz.partial"
    with ds.open("rb") as inp, tmp.open("wb") as raw, gzip.GzipFile(filename="startup.ds",mode="wb",compresslevel=3,fileobj=raw,mtime=0) as out:
        shutil.copyfileobj(inp,out,length=1024*1024)
    with gzip.open(tmp,"rb") as inp:
        recovered=digest(inp)
    with ds.open("rb") as inp:
        original=digest(inp)
    assert original==recovered
    with tmp.open("rb") as inp:
        archive=digest(inp)
    tmp.replace(target)
    (HERE/"archive.json").write_text(json.dumps({"dataset":"startup.ds","original_bytes":original[0],"original_sha256":original[1],
                        "archive":"startup.ds.gz","compressed_bytes":archive[0],"compressed_sha256":archive[1],
                        "round_trip_verified":True},indent=2)+"\n",encoding="ascii")


def recover(verify_only):
    record=json.loads((HERE/"archive.json").read_text(encoding="ascii"))
    target=HERE/"startup.ds"
    compressed=HERE/"startup.ds.gz"
    expected=(record["original_bytes"],record["original_sha256"])
    with compressed.open("rb") as f:
        if digest(f)!=(record["compressed_bytes"],record["compressed_sha256"]):
            raise ValueError("archive size or SHA-256 differs; check git lfs pull and fsck")
    if verify_only:
        with gzip.open(compressed,"rb") as f:
            if digest(f)!=expected:
                raise ValueError("decompressed SHA-256 or size differs from original")
        print("Verified archive and original native dataset hashes")
        return
    if target.exists():
        with target.open("rb") as f:
            if digest(f)!=expected:
                raise ValueError("a different native dataset already occupies the restoration path")
        print("The exact native dataset is already restored")
        return
    partial=HERE/"startup.ds.partial"
    try:
        with gzip.open(compressed,"rb") as f, partial.open("xb") as out:
            shutil.copyfileobj(f,out,length=1024*1024)
        with partial.open("rb") as f:
            if digest(f)!=expected:
                raise ValueError("decompressed SHA-256 or size differs from original")
        if os.name == "nt":
            partial.rename(target)
        else:
            os.link(partial,target)
            partial.unlink()
        print("Restored and verified the native dataset")
    except FileExistsError:
        raise
    except Exception:
        partial.unlink(missing_ok=True)
        raise


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    action=parser.add_mutually_exclusive_group()
    action.add_argument("--verify",action="store_true")
    action.add_argument("--restore",action="store_true")
    opts=parser.parse_args()
    if opts.restore or opts.verify:
        recover(opts.verify)
    else:
        archive()
