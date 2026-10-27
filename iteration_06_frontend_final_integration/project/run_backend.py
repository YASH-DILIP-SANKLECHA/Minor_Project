"""Start the local FastAPI server safely for long-running refinements.

Do not use Uvicorn's development reloader for this project. The reloader
watches the dataset files, and saving a raw/refined file would restart the
process that owns the background refinement job.
"""

from __future__ import annotations

import uvicorn


if __name__ == "__main__":
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=False)
