import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { STLLoader } from 'three/addons/loaders/STLLoader.js';

// DOM Elements
const chatHistory = document.getElementById('chat-history');
const userInput = document.getElementById('user-input');
const sendBtn = document.getElementById('send-btn');
const loadingOverlay = document.getElementById('loading-overlay');
const downloadControls = document.getElementById('download-controls');
const jsonViewer = document.getElementById('json-viewer');

// State
let scene, camera, renderer, controls;
let currentMesh = null;

// Initialize 3D Viewer
function initViewer() {
    const container = document.getElementById('3d-container');

    scene = new THREE.Scene();
    scene.add(new THREE.GridHelper(500, 50));

    // Lights
    const ambientLight = new THREE.AmbientLight(0x404040, 2);
    scene.add(ambientLight);

    const dirLight = new THREE.DirectionalLight(0xffffff, 2);
    dirLight.position.set(50, 50, 50);
    scene.add(dirLight);

    const backLight = new THREE.DirectionalLight(0xffffff, 1);
    backLight.position.set(-50, 50, -50);
    scene.add(backLight);

    // Camera
    camera = new THREE.PerspectiveCamera(45, container.clientWidth / container.clientHeight, 1, 2000);
    camera.position.set(100, 100, 100);

    // Renderer
    renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(container.clientWidth, container.clientHeight);
    container.appendChild(renderer.domElement);

    // Controls
    controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;

    // Animation Loop
    function animate() {
        requestAnimationFrame(animate);
        controls.update();
        renderer.render(scene, camera);
    }
    animate();

    // Resize Handler
    window.addEventListener('resize', () => {
        camera.aspect = container.clientWidth / container.clientHeight;
        camera.updateProjectionMatrix();
        renderer.setSize(container.clientWidth, container.clientHeight);
    });
}

function loadSTL(url) {
    if (currentMesh) {
        scene.remove(currentMesh);
        currentMesh = null;
    }

    const loader = new STLLoader();
    loader.load(
        url,
        function (geometry) {
            const material = new THREE.MeshPhysicalMaterial({
                color: 0x00aaff,
                metalness: 0.2,
                roughness: 0.5,
                clearcoat: 1.0,
                clearcoatRoughness: 0.1
            });
            const mesh = new THREE.Mesh(geometry, material);

            // Center the geometry
            geometry.center();

            // Rotate to match typical CAD orientation (Z-up vs Y-up)
            mesh.rotation.x = -Math.PI / 2;

            scene.add(mesh);
            currentMesh = mesh;

            // Fit camera to object
            const box = new THREE.Box3().setFromObject(mesh);
            const size = box.getSize(new THREE.Vector3()).length();
            const center = box.getCenter(new THREE.Vector3());

            controls.target.copy(center);
            camera.position.set(center.x + size, center.y + size, center.z + size);
            controls.update();

            // Auto-rotate effect briefly
            // let rotateCount = 0;
            // function introSpin() {
            //    if (rotateCount < 100) {
            //        mesh.rotation.z += 0.05;
            //        rotateCount++;
            //        requestAnimationFrame(introSpin);
            //    }
            // }
            // introSpin();
        },
        (xhr) => {
            console.log((xhr.loaded / xhr.total * 100) + '% loaded');
        },
        (error) => {
            console.error('An error happened', error);
            addMessage("system", "Failed to load 3D model visualization.");
        }
    );
}

// Chat Logic
function addMessage(role, text) {
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${role}`;

    const bubble = document.createElement('div');
    bubble.className = 'bubble';
    bubble.innerText = text;

    msgDiv.appendChild(bubble);
    chatHistory.appendChild(msgDiv);
    chatHistory.scrollTop = chatHistory.scrollHeight;
}

async function handleSend() {
    const text = userInput.value.trim();
    if (!text) return;

    // Add user message
    addMessage('user', text);
    userInput.value = '';

    // Show loading
    loadingOverlay.classList.remove('hidden');
    downloadControls.style.display = 'none';

    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: text })
        });

        if (!response.ok) {
            const errData = await response.json();
            throw new Error(errData.detail || `Server Error: ${response.status}`);
        }

        const data = await response.json();

        if (data.type === 'text') {
            addMessage('system', data.message);
        } else if (data.type === 'model') {
            addMessage('system', data.message);

            // Populate JSON Viewer
            jsonViewer.textContent = JSON.stringify({
                template: data.template,
                params: data.params,
                files: data.files
            }, null, 2);

            // Load STL
            loadSTL(data.files.stl);

            // Update Download Links
            document.getElementById('download-step').href = data.files.step;
            document.getElementById('download-step').download = `${data.template}.step`;

            document.getElementById('download-stl').href = data.files.stl;
            document.getElementById('download-stl').download = `${data.template}.stl`;

            document.getElementById('download-script').href = data.files.script;

            // Show result UI
            downloadControls.style.display = 'flex';
        }

    } catch (err) {
        addMessage('system', `Error: ${err.message}`);
        console.error(err);
    } finally {
        loadingOverlay.classList.add('hidden');
    }
}

// Event Listeners
sendBtn.addEventListener('click', handleSend);
userInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') handleSend();
});

// Tab Switching
document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        // Remove active class from all
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));

        // Add active to clicked
        btn.classList.add('active');
        const tabId = btn.getAttribute('data-tab');
        document.getElementById(`${tabId}-tab`).classList.add('active');
    });
});

// Start
initViewer();
