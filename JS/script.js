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

// onclick event -on map
map.on('click', async (e) => {
    const lat = e.latlng.lat;
    const lng = e.latlng.lng;
    // Clean the map
    mapLayers.routes.clearLayers();
    mapLayers.markers.clearLayers();

    // Show loading popup at clicked location
    if (currentPopup) map.closePopup(currentPopup);
    currentPopup = L.popup({ closeButton: false })
        .setLatLng([lat, lng])
        .setContent('Loading...')
        .openOn(map);

    // Call backend API
    try {
        const response = await fetch(`https://yorkstudy-whatsnearby.onrender.com/analyze?`,{
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ lat, lng })
            });
        if (!response.ok) {
            results.innerHTML = "Server error or no response.";
            return;
        }
        const data = await response.json();
        // Show result in popup, draw route and tags
        showAnalysisResultOnMap(lat, lng, data);

    } catch (err) {
        results.innerHTML = "Error fetching accessibility data.";
    }
});

function showAnalysisResultOnMap(lat, lng, data) {
    // Collect result html for popup
    const { location, nearest_gp_surgery, nearest_hospital, nearest_pharmacy } = data;
    const makeHtml = (facility, type) => {
        if (!facility.feature)
            return `<b>${type}:</b> <span style="color:#aaa">N/A</span><br>`;
        return `<b>${type}:</b> ${facility.feature.name || 'N/A'}<br>distance: ${facility.distance || '?'}m Approximate walk: ${facility.walk_time || '?'}分鐘<br>`;
    };

    let html = `<div style="min-width:180px">
        <b>Analysis results</b><br>
        your location：<br>
        <span style="color:#555">${location[0].toFixed(5)}, ${location[1].toFixed(5)}</span><br><hr>
        ${makeHtml(nearest_gp_surgery, 'GP surgery')}
        ${makeHtml(nearest_hospital, 'Hospital')}
        ${makeHtml(nearest_pharmacy, 'Pharmacy')}
    </div>`;

    // Show popup
    if (currentPopup) map.closePopup(currentPopup);
    currentPopup = L.popup()
        .setLatLng([lat, lng])
        .setContent(html)
        .openOn(map);

    // User marker
    L.marker([lat, lng], {
        icon: L.divIcon({
            className: 'user-location-marker',
            html: '📍',
            iconSize: [30, 30]
        })
    }).addTo(mapLayers.markers);

    // Optionally, draw route & tag 
    // asume Flask return data w/ nearest_* w/ path arrtibute，e.g. [[lat, lng], ...]
    const facilities = [
        { key: 'nearest_gp_surgery', color: '#3388ff', tag: '🏥', label: 'GP' },
        { key: 'nearest_hospital', color: '#ff3333', tag: '🏨', label: 'Hospital' },
        { key: 'nearest_pharmacy', color: '#33bb33', tag: '💊', label: 'Pharmacy' }
    ];

    facilities.forEach(fac => {
        const facility = data[fac.key];
        if (facility && facility.path && Array.isArray(facility.path) && facility.path.length > 1) {
            // Draw route
            L.polyline(facility.path, {
                color: fac.color,
                weight: 4,
                opacity: 0.7,
                dashArray: '5, 5'
            }).addTo(mapLayers.routes);

            // Add destination tag
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

    // re-load facilities point
    loadGeoJSONData();
}

// init
loadGeoJSONData();