# Netlify deployment

## Deploy from this project

Connect the repository or project folder at `E:\Land tech\LandGuardBD_MVP` to Netlify. In Netlify site settings, leave **Base directory** blank. The root `netlify.toml` already configures:

- Repository root as the build directory
- Build command: `npm run build`
- Publish directory: `LandGuardBD/frontend/dist`
- SPA routing fallback to `index.html`

## Drag and drop

Upload `output/netlify/jomicheck-bd-netlify-complete.zip` to Netlify, or upload the extracted contents of `LandGuardBD/frontend/dist`.

## Demo mode and API mode

If `VITE_API_URL` is left empty, the Netlify site runs in browser-only demo mode. Use `admin / LandGuard123!` to sign in; the 50 synthetic records and verification history are stored in that browser's local storage.

To connect the real FastAPI backend instead, set this Netlify environment variable before building:

```text
VITE_API_URL=https://your-backend-host.example.com/api/v1
```

The FastAPI backend in `LandGuardBD/backend` must be deployed separately and its URL must end with `/api/v1`. Netlify environment-variable changes require a new deploy.
