# SynthoCAD Frontend

Modern web interface for SynthoCAD - AI-Powered CAD Generation Platform

## Features

### 🎨 Generation
- **Natural Language Input**: Describe CAD models in plain English
- **JSON Input**: Upload or paste SCL JSON schemas
- **Quick Examples**: One-click pre-built examples
- **Real-time Validation**: Validate prompts before generation
- **Automatic FreeCAD Integration**: Open models immediately after generation

### � STEP File Preview & Editing
- **Drag-and-Drop Upload**: Drop any `.step` / `.stp` file onto the upload zone
- **7-Angle Annotated Views**: Instantly renders Isometric, Top, Bottom, Front, Back, Left, and Right views with feature labels (cylinders, planes, cones)
- **Thumbnail Strip**: Click any of the 7 thumbnails to switch to that view in the main pane
- **Image Zoom**: Scroll-wheel zoom (0.5× – 6×) plus toolbar `+` / `−` / Reset buttons with live percentage readout
- **Natural-Language Editing**: Enter an edit prompt (e.g. "Make the hole diameter 10mm") and receive a new STEP file based on exact geometric analysis

### �📁 Model Management
- View all generated models
- Open models in FreeCAD with one click
- Search and filter models
- Delete specific models or sets

### ⚙️ Parameter Editor
- Extract editable parameters from generated models
- Real-time parameter modification
- Update and regenerate models with new parameters
- Automatic FreeCAD reload after regeneration

### 🧹 Storage Management
- View storage statistics (file counts, sizes)
- Cleanup by age (delete files older than X days)
- Cleanup by count (keep only N most recent files)
- Dry-run mode for safe preview
- Delete specific models with all related files

### 📊 Monitoring
- Success rate tracking
- Retry statistics
- Operation history
- Error tracking and diagnostics

## Getting Started

### Prerequisites

- Backend API running on `http://localhost:5000`
- Modern web browser (Chrome, Firefox, Edge, Safari)

### Installation

1. **No build process required!** Simply open `index.html` in your browser

2. **Or use a local server** (recommended):

   ```bash
   # Using Python
   cd frontend
   python -m http.server 8000
   # Open http://localhost:8000

   # Using Node.js
   npx serve
   # Open http://localhost:3000

   # Using VS Code Live Server extension
   # Right-click on index.html -> "Open with Live Server"
   ```

### Configuration

The API base URL is configured in `js/api.js`:

```javascript
const API_BASE_URL = 'http://localhost:5000/api/v1';
```

Change this if your backend is running on a different port or host.

## Usage Guide

### 1. Generate from Natural Language

1. Navigate to the **Generate** tab
2. Enter your design description (e.g., "Create a cylinder with 20mm diameter and 50mm height")
3. Optionally validate the prompt first
4. Click **Generate Model**
5. Model will be generated and optionally opened in FreeCAD

### 2. Generate from JSON

1. Navigate to the **Generate** tab, scroll to JSON section
2. Paste your SCL JSON or click **Load JSON File**
3. Optionally specify an output name
4. Click **Generate Model**

### 3. Edit Parameters

1. Navigate to the **Parameters** tab
2. Enter the Python filename (e.g., `output_generated.py`)
3. Click **Extract Parameters**
4. Modify parameter values
5. Click **Update & Regenerate** to create new STEP file

### 4. Manage Storage

1. Navigate to the **Cleanup** tab
2. View current storage statistics
3. Configure cleanup options (age, count, dry-run)
4. Run cleanup operations
5. Delete specific models as needed

### 5. Monitor System

1. Navigate to the **Monitoring** tab
2. View success rates and statistics
3. Filter operation history
4. Diagnose failures

### 6. Preview a STEP File (7-Angle View)

1. In the left panel, find the **Upload & Preview STEP** section
2. Drag-and-drop a `.step` / `.stp` file onto the drop zone, or click to browse
3. Click **Preview** — the backend analyzes geometry and renders 7 annotated images
4. The **Preview** tab activates automatically, showing a **thumbnail strip** of all 7 angles
5. Click any thumbnail to enlarge it in the main viewer
6. Use the **scroll wheel** or toolbar `+` / `−` buttons to zoom in and out
7. Click **100%** in the toolbar to reset zoom

### 7. Edit an Uploaded STEP File

1. After previewing, the **Edit Prompt** area appears below the upload zone
2. Enter a natural-language change (e.g., `"Increase the boss diameter to 15mm"`)
   - The feature IDs shown in the rendered images can be referenced directly (e.g., `"feature C1"`)
3. Click **Edit STEP**
4. A new STEP file is generated and a download link appears in the **STEP** tab

## File Structure

```
frontend/
├── index.html          # Main HTML interface
├── css/
│   └── style.css       # Styling and themes
├── js/
│   ├── api.js          # API client for backend communication
│   └── app.js          # Main application logic
└── README.md           # This file
```

## API Integration

The frontend connects to these backend endpoints:

### Generation
- `POST /api/v1/generate/from-prompt`
- `POST /api/v1/generate/from-json`
- `POST /api/v1/generate/validate-prompt`

### Parameters
- `GET /api/v1/parameters/extract/<filename>`
- `POST /api/v1/parameters/update/<filename>`
- `POST /api/v1/parameters/regenerate/<filename>`

### STEP Preview & Editing
- `POST /api/v1/edit/preview` — Upload STEP → returns 7 annotated image URLs + feature analysis
- `POST /api/v1/edit/from-step` — Upload STEP + prompt → returns new STEP file
- `GET /outputs/previews/<stem>/<view>.png` — Serve a rendered view image

### FreeCAD Viewer
- `GET /api/v1/viewer/check`
- `POST /api/v1/viewer/open`
- `POST /api/v1/viewer/reload`

### Cleanup
- `GET /api/v1/cleanup/stats`
- `POST /api/v1/cleanup/cleanup`
- `POST /api/v1/cleanup/cleanup/by-age`
- `POST /api/v1/cleanup/cleanup/by-count`
- `DELETE /api/v1/cleanup/<model_name>`

### Monitoring
- `GET /api/v1/cleanup/retry-stats`

### Health
- `GET /api/v1/health`

## Browser Compatibility

- ✅ Chrome 90+
- ✅ Firefox 88+
- ✅ Edge 90+
- ✅ Safari 14+

## Customization

### Changing Colors/Theme

Edit CSS variables in `css/style.css`:

```css
:root {
    --primary-color: #2563eb;
    --success-color: #10b981;
    --warning-color: #f59e0b;
    --danger-color: #ef4444;
    /* ... more variables ... */
}
```

### Adding Examples

Edit the `examples` object in `js/app.js`:

```javascript
const examples = {
    myExample: "Your custom prompt here"
};
```

Then add a button in `index.html`:

```html
<button class="example-btn" data-example="myExample">
    My Example<br><small>Description</small>
</button>
```

## Troubleshooting

### Backend Connection Issues

1. Check backend is running: `http://localhost:5000/api/v1/health`
2. Verify CORS is enabled in backend (already configured)
3. Check browser console for errors (F12)

### FreeCAD Not Opening

1. Ensure FreeCAD is installed
2. Check FreeCAD status indicator in header
3. Manually specify FreeCAD path if needed

### Parameters Not Extracting

1. Verify Python file exists in outputs folder
2. Check file name format: `<name>_generated.py`
3. Ensure file was generated successfully

## Development

### Adding New Features

1. **Add UI**: Update `index.html` with new elements
2. **Add API Method**: Add method to `js/api.js`
3. **Add Logic**: Add event handlers and logic to `js/app.js`
4. **Add Styling**: Update `css/style.css`

### Debugging

Open browser console (F12) to view:
- API requests and responses
- JavaScript errors
- Network issues
- State changes

## Performance

- Lightweight (no frameworks)
- Fast page load
- Minimal dependencies
- Efficient API calls

## Security

- No sensitive data stored in browser
- API calls over HTTP (use HTTPS in production)
- Input validation on backend
- No external dependencies

## Future Enhancements

- [ ] Real-time generation progress
- [ ] 3D preview in browser
- [ ] Model comparison tool
- [ ] Export to multiple formats
- [ ] Collaborative features
- [ ] Template marketplace
- [ ] Dark mode toggle
- [ ] Mobile app version

## Support

For issues and questions:
- Check browser console for errors
- Verify backend is running
- Review API endpoint responses
- Check network connectivity

## License

Part of the SynthoCAD project

