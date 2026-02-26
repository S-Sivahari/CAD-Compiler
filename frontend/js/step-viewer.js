/**
 * SynthoCAD - Three.js STEP Viewer
 * Uses occt-import-js (OpenCASCADE WebAssembly) for STEP parsing
 * and Three.js for WebGL rendering with orbit controls.
 */

const stepViewer = (() => {
    // ── Internal State ───────────────────────────────────────────────────────
    let renderer = null;
    let scene = null;
    let camera = null;
    let controls = null;
    let animFrameId = null;
    let currentMeshes = [];
    let isWireframe = false;
    let occtReady = false;
    let occtInstance = null;

    // ── Face Selection State ─────────────────────────────────────────────────
    let raycaster = null;
    let selectedMesh = null;        // currently highlighted mesh
    let selectedOrigMat = null;     // its original material (or array)
    let _selMat = null;             // lazily created on first init()
    let _pointerDownPos = null;     // track pointer position for click vs drag
    const CLICK_THRESHOLD = 4;      // max pixels to still count as a click

    const STATUS = {
        idle: 'Drop or generate a STEP file to view in 3D',
        loading: 'Loading STEP file…',
        occtLoading: 'Initialising geometry engine…',
        error: (msg) => `⚠ ${msg}`,
    };

    // ── Public API ────────────────────────────────────────────────────────────
    async function init() {
        if (renderer) return; // already initialised

        const canvas = document.getElementById('step3d-canvas');
        if (!canvas) return;

        // Renderer
        renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
        renderer.setPixelRatio(window.devicePixelRatio);
        renderer.shadowMap.enabled = true;
        renderer.shadowMap.type = THREE.PCFSoftShadowMap;

        // Scene
        scene = new THREE.Scene();
        scene.background = new THREE.Color(0x1a1a1a);

        // Grid helper (subtle)
        const grid = new THREE.GridHelper(200, 40, 0x2a2a2a, 0x2a2a2a);
        scene.add(grid);

        // Lighting
        const ambient = new THREE.AmbientLight(0xffffff, 0.45);
        scene.add(ambient);

        const hemi = new THREE.HemisphereLight(0xffffff, 0x333344, 0.5);
        scene.add(hemi);

        const dirA = new THREE.DirectionalLight(0xffffff, 0.9);
        dirA.position.set(80, 120, 60);
        dirA.castShadow = true;
        scene.add(dirA);

        const dirB = new THREE.DirectionalLight(0xaabbff, 0.35);
        dirB.position.set(-60, -40, -80);
        scene.add(dirB);

        // Camera
        camera = new THREE.PerspectiveCamera(45, 1, 0.01, 50000);
        camera.position.set(200, 150, 200);

        // OrbitControls — loaded via CDN addons
        controls = new THREE.OrbitControls(camera, canvas);
        controls.enableDamping = true;
        controls.dampingFactor = 0.07;
        controls.minDistance = 0.1;
        controls.maxDistance = 10000;

        // Resize handling
        const container = document.getElementById('step3d-container');
        const ro = new ResizeObserver(() => _resize());
        ro.observe(container);
        _resize();

        // Raycaster for face picking
        raycaster = new THREE.Raycaster();
        _selMat = new THREE.MeshPhongMaterial({
            color: 0xf0a020,            // gold highlight
            emissive: 0x402800,
            specular: 0xffffff,
            shininess: 80,
            side: THREE.DoubleSide,
        });
        canvas.addEventListener('pointerdown', _onPointerDown);
        canvas.addEventListener('pointerup', _onPointerUp);

        // Start render loop
        _renderLoop();

        // Pre-warm the OCCT engine in background
        _loadOcct();
    }

    async function loadStepFile(file) {
        if (!file) return;
        _setStatus(STATUS.loading);
        _clearMeshes();

        try {
            await _ensureOcct();
            const buffer = await file.arrayBuffer();
            await _importAndRender(new Uint8Array(buffer), file.name);
        } catch (err) {
            console.error('[step-viewer] loadStepFile failed:', err);
            _setStatus(STATUS.error(err.message || 'Failed to load STEP file'));
        }
    }

    async function loadStepUrl(url) {
        if (!url) return;
        _setStatus(STATUS.loading);
        _clearMeshes();

        try {
            await _ensureOcct();
            const resp = await fetch(url);
            if (!resp.ok) throw new Error(`HTTP ${resp.status} fetching STEP`);
            const buffer = await resp.arrayBuffer();
            const name = url.split('/').pop() || 'model.step';
            await _importAndRender(new Uint8Array(buffer), name);
        } catch (err) {
            console.error('[step-viewer] loadStepUrl failed:', err);
            _setStatus(STATUS.error(err.message || 'Failed to fetch STEP file'));
        }
    }

    function resetView() {
        if (!scene || currentMeshes.length === 0) return;
        _fitCameraToMeshes();
    }

    function toggleWireframe() {
        isWireframe = !isWireframe;
        currentMeshes.forEach(m => {
            if (m.material) {
                if (Array.isArray(m.material)) {
                    m.material.forEach(mat => { mat.wireframe = isWireframe; });
                } else {
                    m.material.wireframe = isWireframe;
                }
            }
        });
        // Keep the selection highlight material in sync
        if (_selMat) _selMat.wireframe = isWireframe;
        // Keep stored original material in sync so deselect doesn't revert wireframe state
        if (selectedOrigMat) {
            if (Array.isArray(selectedOrigMat)) {
                selectedOrigMat.forEach(mat => { mat.wireframe = isWireframe; });
            } else {
                selectedOrigMat.wireframe = isWireframe;
            }
        }
        const btn = document.getElementById('step3d-btn-wire');
        if (btn) btn.classList.toggle('active', isWireframe);
    }

    function dispose() {
        if (animFrameId) cancelAnimationFrame(animFrameId);
        _clearMeshes();
        if (renderer) {
            const canvas = renderer.domElement;
            canvas.removeEventListener('pointerdown', _onPointerDown);
            canvas.removeEventListener('pointerup', _onPointerUp);
            renderer.dispose();
            renderer = null;
        }
        scene = null; camera = null; controls = null;
        _hideFaceTooltip();
    }

    // ── Private Helpers ───────────────────────────────────────────────────────

    function _renderLoop() {
        animFrameId = requestAnimationFrame(_renderLoop);
        if (controls) controls.update();
        if (renderer && scene && camera) renderer.render(scene, camera);
    }

    function _resize() {
        const container = document.getElementById('step3d-container');
        if (!container || !renderer || !camera) return;
        const w = container.clientWidth;
        const h = container.clientHeight;
        renderer.setSize(w, h);
        camera.aspect = w / h;
        camera.updateProjectionMatrix();
    }

    function _clearMeshes() {
        _deselectFace();    // restore material before disposing
        currentMeshes.forEach(m => {
            if (m.geometry) m.geometry.dispose();
            if (m.material) {
                if (Array.isArray(m.material)) m.material.forEach(mt => mt.dispose());
                else m.material.dispose();
            }
            if (scene) scene.remove(m);
        });
        currentMeshes = [];
        isWireframe = false;
        const btn = document.getElementById('step3d-btn-wire');
        if (btn) btn.classList.remove('active');
        _hideFaceTooltip();
    }

    function _setStatus(msg) {
        const el = document.getElementById('step3d-status');
        if (!el) return;
        el.textContent = msg;
        el.style.display = msg ? 'flex' : 'none';
    }

    async function _loadOcct() {
        if (occtReady || occtInstance) return;
        try {
            _setStatus(STATUS.occtLoading);
            // occt-import-js >= 0.0.14 exposes `occtimportjs` as the global initialiser.
            // The CDN build resolves the .wasm file automatically from the same URL.
            occtInstance = await occtimportjs();
            occtReady = true;
            _setStatus(STATUS.idle);
        } catch (err) {
            console.error('[step-viewer] OCCT init failed:', err);
            _setStatus(STATUS.error('Geometry engine failed to load – check network'));
        }
    }

    async function _ensureOcct() {
        if (occtReady && occtInstance) return;
        await _loadOcct();
        // Wait until ready (with a timeout)
        let waited = 0;
        while (!occtReady && waited < 30000) {
            await _sleep(200);
            waited += 200;
        }
        if (!occtReady) throw new Error('Geometry engine timed out');
    }

    async function _importAndRender(uint8Array, filename) {
        // v0.0.14+: ReadStepFile accepts a Uint8Array directly — no virtual FS needed.
        const result = occtInstance.ReadStepFile(uint8Array, {
            linearDeflection: 0.1,
            angularDeflection: 0.5,
        });


        if (!result || !result.success) {
            throw new Error('OCCT could not parse the STEP file');
        }

        // Build Three.js meshes — ONE per brep_face so each face is individually clickable.
        // occt-import-js gives one mesh per solid; brep_faces[].first/last are triangle-index ranges.
        const meshGroup = new THREE.Group();
        let globalFaceIdx = 0;   // matches step_analyzer.py's face enumeration order

        result.meshes.forEach((occtMesh) => {
            const srcPos = occtMesh.attributes.position
                ? new Float32Array(occtMesh.attributes.position.array) : null;
            const srcNorm = occtMesh.attributes.normal
                ? new Float32Array(occtMesh.attributes.normal.array) : null;
            const srcIdx = occtMesh.index
                ? new Uint32Array(occtMesh.index.array) : null;
            const solidName = occtMesh.name || '';
            const solidColor = occtMesh.color || null;

            const brepFaces = occtMesh.brep_faces && occtMesh.brep_faces.length > 0
                ? occtMesh.brep_faces
                : null;

            if (!brepFaces) {
                // ── Fallback: no face table — add as one solid mesh ──────────
                _addRawMesh(meshGroup, srcPos, srcNorm, srcIdx,
                    solidColor, solidName, `f${globalFaceIdx++}`);
                return;
            }

            // ── One Three.js mesh per brep_face ──────────────────────────────
            brepFaces.forEach((brepFace) => {
                const first = brepFace.first;   // inclusive triangle index
                const last = brepFace.last;    // inclusive triangle index

                // Collect triangle vertex indices for this face only
                const rawIdxBuf = [];
                if (srcIdx) {
                    for (let t = first; t <= last; t++) {
                        rawIdxBuf.push(srcIdx[t * 3], srcIdx[t * 3 + 1], srcIdx[t * 3 + 2]);
                    }
                } else if (srcPos) {
                    // Non-indexed: vertices are already sequential triplets
                    for (let t = first; t <= last; t++) {
                        rawIdxBuf.push(t * 3, t * 3 + 1, t * 3 + 2);
                    }
                }

                if (rawIdxBuf.length === 0) { globalFaceIdx++; return; }

                // Remap to a compact local vertex set
                const uniqueVerts = Array.from(new Set(rawIdxBuf)).sort((a, b) => a - b);
                const remap = new Map(uniqueVerts.map((v, i) => [v, i]));
                const vCount = uniqueVerts.length;

                const pos = new Float32Array(vCount * 3);
                const norm = srcNorm ? new Float32Array(vCount * 3) : null;

                for (let i = 0; i < vCount; i++) {
                    const v = uniqueVerts[i];
                    pos[i * 3] = srcPos[v * 3];
                    pos[i * 3 + 1] = srcPos[v * 3 + 1];
                    pos[i * 3 + 2] = srcPos[v * 3 + 2];
                    if (norm) {
                        norm[i * 3] = srcNorm[v * 3];
                        norm[i * 3 + 1] = srcNorm[v * 3 + 1];
                        norm[i * 3 + 2] = srcNorm[v * 3 + 2];
                    }
                }

                const localIdx = new Uint32Array(rawIdxBuf.map(v => remap.get(v)));

                const geom = new THREE.BufferGeometry();
                geom.setAttribute('position', new THREE.BufferAttribute(pos, 3));
                if (norm) geom.setAttribute('normal', new THREE.BufferAttribute(norm, 3));
                geom.setIndex(new THREE.BufferAttribute(localIdx, 1));
                if (!norm) geom.computeVertexNormals();

                // Colour priority: per-face → solid → default steel-blue
                let color = new THREE.Color(0x7090b0);
                if (brepFace.color) {
                    color = new THREE.Color(
                        brepFace.color[0] / 255,
                        brepFace.color[1] / 255,
                        brepFace.color[2] / 255
                    );
                } else if (solidColor) {
                    color = new THREE.Color(
                        solidColor[0] / 255,
                        solidColor[1] / 255,
                        solidColor[2] / 255
                    );
                }

                const mat = new THREE.MeshPhongMaterial({
                    color,
                    specular: 0x666666,
                    shininess: 60,
                    side: THREE.DoubleSide,
                });

                const mesh = new THREE.Mesh(geom, mat);
                mesh.castShadow = true;
                mesh.receiveShadow = true;
                mesh.userData = {
                    featureId: `f${globalFaceIdx}`,
                    meshName: solidName,
                    origColor: color.clone(),
                };

                globalFaceIdx++;
                meshGroup.add(mesh);
                currentMeshes.push(mesh);
            });
        });

        // ── Helper: add a whole-solid mesh (brep_face fallback) ──────────────────
        function _addRawMesh(group, srcPos, srcNorm, srcIdx, colorArr, name, featureId) {
            if (!srcPos) return;
            const geom = new THREE.BufferGeometry();
            geom.setAttribute('position', new THREE.BufferAttribute(srcPos, 3));
            if (srcNorm) geom.setAttribute('normal', new THREE.BufferAttribute(srcNorm, 3));
            if (srcIdx) geom.setIndex(new THREE.BufferAttribute(srcIdx, 1));
            if (!srcNorm) geom.computeVertexNormals();
            const color = colorArr
                ? new THREE.Color(colorArr[0] / 255, colorArr[1] / 255, colorArr[2] / 255)
                : new THREE.Color(0x7090b0);
            const mat = new THREE.MeshPhongMaterial({ color, specular: 0x666666, shininess: 60, side: THREE.DoubleSide });
            const mesh = new THREE.Mesh(geom, mat);
            mesh.userData = { featureId, meshName: name, origColor: color.clone() };
            group.add(mesh);
            currentMeshes.push(mesh);
        }

        scene.add(meshGroup);
        _setStatus('');   // hide status overlay

        // Fit camera so the model fills the view nicely
        _fitCameraToMeshes();
    }

    function _fitCameraToMeshes() {
        if (currentMeshes.length === 0 || !camera || !controls) return;

        const box = new THREE.Box3();
        currentMeshes.forEach(m => box.expandByObject(m));

        if (box.isEmpty()) return;

        const center = new THREE.Vector3();
        const size = new THREE.Vector3();
        box.getCenter(center);
        box.getSize(size);

        const maxDim = Math.max(size.x, size.y, size.z);
        const fov = camera.fov * (Math.PI / 180);
        let camDist = Math.abs(maxDim / 2 / Math.tan(fov / 2)) * 1.8;

        camera.position.copy(center);
        camera.position.z += camDist;
        camera.position.y += camDist * 0.4;
        camera.position.x += camDist * 0.3;
        camera.near = camDist / 1000;
        camera.far = camDist * 100;
        camera.updateProjectionMatrix();

        controls.target.copy(center);
        controls.update();
    }

    function _sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    // ── Face picking ──────────────────────────────────────────────────────────

    function _onPointerDown(event) {
        _pointerDownPos = { x: event.clientX, y: event.clientY };
    }

    function _onPointerUp(event) {
        if (!_pointerDownPos) return;
        const dx = event.clientX - _pointerDownPos.x;
        const dy = event.clientY - _pointerDownPos.y;
        const dist = Math.sqrt(dx * dx + dy * dy);
        _pointerDownPos = null;

        // Only treat as a "click" if the pointer barely moved (not an orbit drag)
        if (dist > CLICK_THRESHOLD) return;

        _doFacePick(event);
    }

    function _doFacePick(event) {
        if (!renderer || !camera || currentMeshes.length === 0) return;

        const canvas = renderer.domElement;
        const rect = canvas.getBoundingClientRect();
        const mouse = new THREE.Vector2(
            ((event.clientX - rect.left) / rect.width) * 2 - 1,
            ((event.clientY - rect.top) / rect.height) * -2 + 1
        );

        raycaster.setFromCamera(mouse, camera);
        const hits = raycaster.intersectObjects(currentMeshes, false);

        if (hits.length === 0) {
            _deselectFace();
            _hideFaceTooltip();
            return;
        }

        const hit = hits[0];
        const mesh = hit.object;

        if (mesh === selectedMesh) {
            _deselectFace();
            _hideFaceTooltip();
            return;
        }

        _deselectFace();

        selectedMesh = mesh;
        selectedOrigMat = mesh.material;
        mesh.material = _selMat;

        _showFaceTooltip(event.clientX, event.clientY, mesh);
    }

    function _deselectFace() {
        if (!selectedMesh) return;
        selectedMesh.material = selectedOrigMat;
        selectedMesh = null;
        selectedOrigMat = null;
    }

    function _showFaceTooltip(clientX, clientY, mesh) {
        let tip = document.getElementById('step3d-face-tip');
        if (!tip) return;

        const fid = mesh.userData.featureId || '?';

        // Compute bounding-box dimensions of this face's geometry
        let dimStr = '';
        try {
            mesh.geometry.computeBoundingBox();
            const bb = mesh.geometry.boundingBox;
            const sz = new THREE.Vector3();
            bb.getSize(sz);
            const fmt = v => v.toFixed(2);
            dimStr = `${fmt(sz.x)} × ${fmt(sz.y)} × ${fmt(sz.z)} mm`;
        } catch (_) { /* geometry not ready */ }

        // Build display lines
        const lines = [`<span class="face-tip-id">${fid}</span>`];
        if (dimStr) lines.push(`<span class="face-tip-name">${dimStr}</span>`);

        tip.innerHTML = lines.join('');
        tip.style.display = 'block';

        // Position just above the cursor, inside the container
        const container = document.getElementById('step3d-container');
        const cRect = container.getBoundingClientRect();
        let tx = clientX - cRect.left + 14;
        let ty = clientY - cRect.top - 10;

        // Keep within bounds (rough)
        const TW = 200, TH = 60;
        if (tx + TW > cRect.width) tx = clientX - cRect.left - TW - 10;
        if (ty + TH > cRect.height) ty = clientY - cRect.top - TH - 6;
        if (ty < 4) ty = 4;

        tip.style.left = `${tx}px`;
        tip.style.top = `${ty}px`;
    }

    function _hideFaceTooltip() {
        const tip = document.getElementById('step3d-face-tip');
        if (tip) tip.style.display = 'none';
    }

    // ── Public surface ────────────────────────────────────────────────────────
    return { init, loadStepFile, loadStepUrl, resetView, toggleWireframe, dispose };
})();
