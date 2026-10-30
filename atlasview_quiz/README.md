<<<<<<< HEAD
# medverse-3d-viewer
Standalone web-based 3D viewer for visualizing and interacting with anatomical models extracted by the MedVerse Asset Ingestion pipeline. Supports browser-based model inspection on desktop and mobile devices, independently of the VR client and web dashboard.
=======
# AtlasView — Self-Contained Docker Image

This package is designed so the **website and `model.glb` are baked into the Docker image**.
The runtime container does not need a mounted `web/` folder, a local model file, Node.js, npm, or Blender.

## Build

From this directory:

```bash
docker build -t atlasview:latest .
```

## Run

```bash
docker run -d --name atlasview -p 8080:80 --restart unless-stopped atlasview:latest
```

Open:

```text
http://localhost:8080
```

## Docker Compose

```bash
docker compose up -d --build
```

Then open `http://localhost:8080`.

## Publish to Docker Hub

Replace `YOUR_USERNAME` with your Docker Hub username:

```bash
docker login
docker build -t YOUR_USERNAME/atlasview:latest .
docker push YOUR_USERNAME/atlasview:latest
```

Anyone can then run:

```bash
docker pull YOUR_USERNAME/atlasview:latest
docker run -d --name atlasview -p 8080:80 --restart unless-stopped YOUR_USERNAME/atlasview:latest
```

No project files are required on the user's machine after the image is pulled.

## Contents

```text
atlasview_image/
├── Dockerfile
├── nginx.conf
├── docker-compose.yml
├── .dockerignore
├── README.md
└── web/
    ├── index.html
    └── model.glb
```

The anatomical model is inside the image at `/usr/share/nginx/html/model.glb`.
>>>>>>> fc9b08d (MedVerse 3d viewer and quiz)
