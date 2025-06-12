// init-map
const map = L.map('map').setView([53.9624, -1.0819], 13);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(map);

// store map layer
const mapLayers = {
    markers: L.layerGroup().addTo(map),
    routes: L.layerGroup().addTo(map)
};

// load geojson file fm github
async function loadGeoJSONData() {
    const types = ['GP_Surgeries', 'hospital', 'Pharmacies'];
    const promises = types.map(type => 
        fetch(`data/${type}.geojson`)
            .then(response => response.json())
            .then(data => {
                // add the facilites on the map
                L.geoJSON(data, {
                    pointToLayer: (feature, latlng) => {
                        const iconColor = {
                            GP_Surgeries: 'blue',
                            hospitals: 'red',
                            pharmacies: 'green'
                        }[type];
                        
                        return L.circleMarker(latlng, {
                            radius: 6,
                            fillColor: iconColor,
                            color: '#fff',
                            weight: 1,
                            opacity: 1,
                            fillOpacity: 0.8
                        });
                    },
                    onEachFeature: (feature, layer) => {
                         layer.bindPopup(`${type.replace('_', ' ').replace('Pharmacies','Pharmacy')}: ${feature.properties.name}`);
                    }
                }).addTo(mapLayers.markers);
                
                return { type, data };
            })
    );
    
    return Promise.all(promises);
}
let currentPopup = null;

let loadingState = {
    totalSteps: 5, 
    currentStep: 0,
    message: ""
};
// onclick event -on map
map.on('click', async (e) => {
    const lat = e.latlng.lat;
    const lng = e.latlng.lng;
    // Clean the map
    mapLayers.routes.clearLayers();
    mapLayers.markers.clearLayers();
    document.getElementById('accessibility-result').innerHTML = '';
    updateLoadingState(1, "connecting our server...");

    // Rander path:https://yorkstudy-whatsnearby.onrender.com
    try {
        updateLoadingState(2, "sending the location...");
        const response = await fetch(`https://yorkstudy-whatsnearby.onrender.com/analyze?`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ lat, lng })
        });

        if (!response.ok) {
            updateLoadingState(5, "Server error or no response", true);
            showErrorInSidebar("Server error or no response");
            return;
        }

        updateLoadingState(3, "Data analysis in progress...");
        const data = await response.json();

        updateLoadingState(4, "Rendering results...");
        showAnalysisResultOnMap(lat, lng, data);
        showResultsInSidebar(data);

        updateLoadingState(5, "Analysis finished!", true);
    } catch (err) {
        updateLoadingState(5, "Error fetching data: " + err.message, true);
        showErrorInSidebar("Error fetching data: " + err.message);
    }
});

// show result in sidebar
function showResultsInSidebar(data) {
    const { location, postcode, nearest_gp_surgery, nearest_hospital, nearest_pharmacy } = data;
    const sidebar = document.getElementById('accessibility-result');
    const now = new Date();
    
    const makeHtml = (facility, type) => {
        if (!facility.feature)
            return `<div class="result-item"><b>${type}:</b> <span class="na">N/A</span></div>`;
        return `
            <div class="result-item">
                <b>${type}:</b> ${facility.feature.name || 'N/A'}<br>
                <span class="detail">distance: ${facility.distance || '?'}m</span><br>
                <span class="detail">Approximate walk: ${facility.walk_time || '?'}min</span>
            </div>
        `;
    };

    sidebar.innerHTML = `
        <div class="sidebar-results">
            <h3>Results of the analysis</h3>
            <div class="location-info">
                <b>location:</b><br>
                <span class="detail">lat/lon: ${location[0].toFixed(5)}, ${location[1].toFixed(5)}</span><br>
                ${postcode ? `<span class="detail">postcode: ${postcode}</span>` : ''}
                <small class="detail">Last updated: ${now.toLocaleTimeString()}</small>
            </div>
            <hr>
            ${makeHtml(nearest_gp_surgery, 'GP-surgery')}
            ${makeHtml(nearest_hospital, 'Hospital')}
            ${makeHtml(nearest_pharmacy, 'Pharmacy')}
        </div>
    `;
}

// show error msg in sidebar
function showErrorInSidebar(message) {
    const sidebar = document.getElementById('accessibility-result');
    sidebar.innerHTML = `
        <div class="error-message">
            <h3>Error</h3>
            <p>${message}</p>
            <p>Please try clicking another location or try again later.。</p>
        </div>
    `;
}

// update-reload
function updateLoadingState(step, message, isFinal = false) {
    loadingState.currentStep = step;
    loadingState.message = message;
    
    const sidebar = document.getElementById('accessibility-result');
    const progressPercent = (step / loadingState.totalSteps) * 100;
    
    if (!sidebar.innerHTML.includes("sidebar-results")) {
        sidebar.innerHTML = `
            <div class="loading-container">
                <h3>Analyzing location...</h3>
                <div class="progress-bar">
                    <div class="progress" style="width: ${progressPercent}%"></div>
                </div>
                <p class="loading-message">${message}</p>
                <small>Step ${step}/${loadingState.totalSteps}</small>
            </div>`
    };
    
    if (isFinal && !sidebar.innerHTML.includes("sidebar-results")) {
        //show in the sidebar during analysis
        setTimeout(() => {
            if (sidebar.innerHTML.includes("Analyzing location...")) {
                sidebar.innerHTML = '<p>Click a location on the map to analyze.</p>';
            }
        }, 2000);
    }
}

function showAnalysisResultOnMap(lat, lng, data) {
    // add tag
    L.marker([lat, lng], {
        icon: L.divIcon({
            className: 'user-location-marker',
            html: '📍',
            iconSize: [30, 30]
        })
    }).addTo(mapLayers.markers);

    // rendering 
    const facilities = [
        { key: 'nearest_gp_surgery', color: '#3388ff', tag: '🏥', label: 'GP' },
        { key: 'nearest_hospital', color: '#ff3333', tag: '🏨', label: 'Hospital' },
        { key: 'nearest_pharmacy', color: '#33bb33', tag: '💊', label: 'Pharmacy' }
    ];

    facilities.forEach(fac => {
        const facility = data[fac.key];
        if (facility && facility.path && Array.isArray(facility.path) && facility.path.length > 1) {
            L.polyline(facility.path, {
                color: fac.color,
                weight: 4,
                opacity: 0.7,
                dashArray: '5, 5'
            }).addTo(mapLayers.routes);

            const endPoint = facility.path[facility.path.length - 1];
            L.marker(endPoint, {
                icon: L.divIcon({
                    className: `${fac.label}-marker`,
                    html: `<span style="font-size:20px">${fac.tag}</span>`,
                    iconSize: [25, 25]
                })
            }).addTo(mapLayers.markers);
        }
    });

    // reload
    loadGeoJSONData();
}