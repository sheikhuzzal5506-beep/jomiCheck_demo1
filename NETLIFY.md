# Netlify deployment

## Deploy from this project

Connect the repository or project folder at `E:\Land tech\LandGuardBD_MVP` to Netlify. The root `netlify.toml` already configures:

- Base directory: `LandGuardBD/frontend`
- Build command: `npm run build`
- Publish directory: `dist`
- SPA routing fallback to `index.html`

## Drag and drop

Upload `output/netlify/jomicheck-bd-netlify-complete.zip` to Netlify, or upload the extracted contents of `LandGuardBD/frontend/dist`.

## Connect the API

The Netlify deployment is the frontend. Set this Netlify environment variable before building:

```text
VITE_API_URL=https://your-backend-host.example.com/api/v1
```

The FastAPI backend in `LandGuardBD/backend` must be deployed separately and its URL must end with `/api/v1`.
