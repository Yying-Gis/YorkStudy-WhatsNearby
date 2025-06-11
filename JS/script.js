map.on('click', async function(e) {
    const lat = e.latlng.lat;
    const lng = e.latlng.lng;

    // 呼叫 Flask API
    const res = await fetch('https://你的-flask-api.onrender.com/analyze', {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({lat, lng})
    });
    const data = await res.json();

    // 組成popup內容
    let html = `<h3>Accessibility Result</h3>
        <ul style="padding-left:16px;">
            <li><strong>Library:</strong> ${data.nearest_library.feature?.name || 'N/A'} (${data.nearest_library.walk_time} min)</li>
            <li><strong>Supermarket:</strong> ${data.nearest_supermarket.feature?.name || 'N/A'} (${data.nearest_supermarket.walk_time} min)</li>
            <li><strong>Restaurant:</strong> ${data.nearest_restaurant.feature?.name || 'N/A'} (${data.nearest_restaurant.walk_time} min)</li>
            <li><strong>Station:</strong> ${data.nearest_station.feature?.name || 'N/A'} (${data.nearest_station.walk_time} min)</li>
            <li><strong>Bus Stop:</strong> ${data.nearest_bus_stop.feature?.name || 'N/A'} (${data.nearest_bus_stop.walk_time} min)</li>
            <li><strong>Hospital:</strong> ${data.nearest_hospital.feature?.name || 'N/A'} (${data.nearest_hospital.walk_time} min)</li>
            <li><strong>Pharmacy:</strong> ${data.nearest_pharmacy.feature?.name || 'N/A'} (${data.nearest_pharmacy.walk_time} min)</li>
            <li><strong>GP Surgery:</strong> ${data.nearest_gp_surgery.feature?.name || 'N/A'} (${data.nearest_gp_surgery.walk_time} min)</li>
            <li><strong>School:</strong> ${data.nearest_school.feature?.name || 'N/A'} (${data.nearest_school.walk_time} min)</li>
        </ul>`;

    // 在地圖上顯示 popup
    L.popup()
      .setLatLng([lat, lng])
      .setContent(html)
      .openOn(map);
});