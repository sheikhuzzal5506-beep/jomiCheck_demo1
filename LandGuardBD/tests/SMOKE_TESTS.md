# Manual smoke-test checklist

- [ ] `GET /api/v1/health` returns `status: ok`.
- [ ] Login succeeds with local demo credentials.
- [ ] Dashboard shows 25 demo deeds.
- [ ] Search `DEMO-2024-001` returns the seeded synthetic deed.
- [ ] A valid JPG/PNG/PDF plus the prefilled fields returns `MATCHED`.
- [ ] Change dag `D-301` to `D-999`: returns `MISMATCH_FOUND`.
- [ ] Change deed number to `NOT-A-DEED`: returns `UNVERIFIABLE`.
- [ ] Download a PDF report for a completed check.
- [ ] Verification history lists the check.
- [ ] Audit log records verification creation and report download.
- [ ] Switch to বাংলা and confirm primary navigation and main workflow labels are translated.
