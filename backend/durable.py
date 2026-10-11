"""Low-volume SQLite checkpoints with conditional Cloud Storage writes.
Database files are local; they are never opened on a FUSE mount.
Generation preconditions prevent silent lost updates across overlapping revisions.
"""

import gzip, os, sqlite3, tempfile
from pathlib import Path
from engine import Engine


class StateConflict(Exception):
    pass


class DurableState:
    def __init__(self, blob=None, path=None):
        self.path = Path(path or os.getenv("DATABASE_PATH", ".data/impactguard.db"))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if blob is None:
            from google.cloud import storage
            from cloud_identity import credentials, runtime_ready

            if not runtime_ready():
                raise ValueError(
                    "Durable cloud state requires the selected Cloud Run identity"
                )
            self.blob = (
                storage.Client(
                    project=os.environ["IMPACTGUARD_VERTEX_PROJECT"],
                    credentials=credentials(),
                )
                .bucket(os.environ["IMPACTGUARD_STORAGE_BUCKET"])
                .blob("state.sqlite3.gz")
            )
        else:
            self.blob = blob
        self.generation = None

    def refresh(self, engine=None, force=False):
        self.blob.reload(timeout=30)
        generation = int(self.blob.generation)
        if not force and generation == self.generation:
            return engine
        payload = self.blob.download_as_bytes(
            if_generation_match=generation, timeout=30
        )
        data = gzip.decompress(payload)
        with tempfile.NamedTemporaryFile(dir=self.path.parent, delete=False) as out:
            temp = Path(out.name)
            out.write(data)
        if engine:
            engine.db.close()
        os.replace(temp, self.path)
        self.generation = generation
        return Engine(str(self.path))

    def open(self):
        try:
            return self.refresh()
        except Exception as e:
            if getattr(e, "code", None) != 404:
                raise
        self.generation = 0
        engine = Engine(str(self.path))
        try:
            self.persist(engine)
        except StateConflict:
            engine = self.refresh(engine, force=True)
        return engine

    def persist(self, engine):
        with tempfile.TemporaryDirectory(dir=self.path.parent) as folder:
            snapshot = Path(folder) / "checkpoint.db"
            target = sqlite3.connect(snapshot)
            try:
                engine.db.backup(target)
            finally:
                target.close()
            compressed = Path(folder) / "checkpoint.gz"
            with snapshot.open("rb") as src, gzip.open(compressed, "wb") as out:
                import shutil

                shutil.copyfileobj(src, out)
            try:
                self.blob.upload_from_filename(
                    str(compressed),
                    content_type="application/gzip",
                    if_generation_match=self.generation,
                    timeout=60,
                )
            except Exception as e:
                if getattr(e, "code", None) == 412:
                    raise StateConflict(
                        "State changed in another instance; retry the request"
                    ) from None
                raise
            self.generation = int(self.blob.generation)
