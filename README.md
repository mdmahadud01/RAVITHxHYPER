# HyperTrade — Railway deployment

All application files are placed directly in the repository root so Railpack can detect the Python project.

## Deploy
1. Upload the CONTENTS of this folder to the root of your GitHub repository (do not upload the enclosing folder).
2. Connect the repository to Railway and use the repository root as the Root Directory.
3. Keep the builder set to Railpack (or automatic).
4. Add required environment variables in Railway Variables. Never commit tokens or credentials.
5. Deploy. The start command is `python HyperTrade.py`.

Python version: 3.11. PyQuotex is bundled in `pyquotex/`; dependencies are listed in `requirements.txt`.
