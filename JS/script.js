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
    const types = ['libraries', 'hospitals', 'pharmacies'];
    const promises = types.map(type => 
        fetch(`data/${type}.geojson`)
            .then(response => response.json())
            .then(data => {
                // add the facilites on the map
                L.geoJSON(data, {
                    pointToLayer: (feature, latlng) => {
                        const iconColor = {
                            libraries: 'blue',
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
                        layer.bindPopup(`${type.slice(0, -1)}: ${feature.properties.name}`);
                    }
                }).addTo(mapLayers.markers);
                
                return { type, data };
            })
    );
    
    return Promise.all(promises);
}

// onclick event -on map
map.on('click', async (e) => {
    const lat = e.latlng.lat;
    const lng = e.latlng.lng;
    const results = document.getElementById('accessibility-result');
    results.innerHTML = 'Loading...';
    
    //clean the map
    mapLayers.routes.clearLayers();

    // call back endAPI
    try {
      /*  const response = await fetch('http://localhost:5000/analyze', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ lat, lng })
        });*/
        const response = await fetch(`https://yorkstudy-whatsnearby.onrender.com/analyze?lat=${lat}&lng=${lng}`);
        if (!response.ok) {
            results.innerHTML = "Server error or no response.";
            return;
        }
        const data = await response.json();

        displayResults(data);
        drawPathsOnMap(data);
    } catch (err) {
        results.innerHTML = "Error fetching accessibility data.";
    }
});
/*
function displayResults(data) {
    const { location, nearest_library, nearest_hospital, nearest_pharmacy } = data;
    const resultsDiv = document.getElementById('accessibility-result');
    
    let result = `
        <h3>result of Accessibility analysis</h3>
        <p><strong> point:</strong> ${location[0].toFixed(6)}, ${location[1].toFixed(6)}</p>
    `;
    
    const createFacilityHTML = (facility, type) => {
        if (!facility.feature) return `<p>there is no ${type}</p>`;
        return `
            <p><strong>the nearest ${type}:</strong> ${facility.feature.name}</p>
            <p>distance: ${facility.distance} M | WALKING TIME ${facility.walk_time} MINS </p>
        `;
    };

    result += createFacilityHTML(nearest_library, 'Library');
    result += createFacilityHTML(nearest_hospital, 'hospital');
    result += createFacilityHTML(nearest_pharmacy, 'Pharmacy');
    
    resultsDiv.innerHTML = html;
}

  
function drawPathsOnMap(data) {
    const { location } = data;
    
    // add tag
    L.marker(location, {
        icon: L.divIcon({
            className: 'user-location-marker',
            html: '📍',
            iconSize: [30, 30]
        })
    }).addTo(mapLayers.markers);
    
    // draw the path of all facilites 
    const pathColors = {
        library: '#3388ff',
        hospital: '#ff3333',
        pharmacy: '#33ff33'
    };
    
    for (const [key, facility] of Object.entries(data)) {
        if (key.startsWith('nearest_') && facility.path) {
            const type = key.replace('nearest_', '');
            
            L.polyline(facility.path, {
                color: pathColors[type],
                weight: 4,
                opacity: 0.7,
                dashArray: '5, 5'
            }).addTo(mapLayers.routes);
            
            // add facilites tag
            if (facility.feature) {
                const endPoint = facility.path[facility.path.length - 1];
                L.marker(endPoint, {
                    icon: L.divIcon({
                        className: `${type}-marker`,
                        html: '🏁',
                        iconSize: [25, 25]
                    })
                }).addTo(mapLayers.markers);
            }
        }
    }
}  


/*

function findNearest(point, features, mode) {
    let nearest = null;
    let minDistance = Infinity;
    
    // Run Turf.js to find the nearest 
    for (const feature of features.features) {
        const distance = turf.distance(point, feature, {units: 'kilometers'});
        if (distance < minDistance) {
            minDistance = distance;
            nearest = feature;
        }
    }
  
    // estimate (speed of walk: 5km/h, spped of drive: 30km/h)
    const speed = mode === 'walking' ? 5 : 30;
    const time = Math.round((minDistance / speed) * 60);
    
    return {
        ...nearest,
        distance: minDistance,
        time: time
    };
}
*/ 

// init
loadGeoJSONData();