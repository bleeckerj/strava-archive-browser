window.ArchiveMap = (() => {
  function segments(payload) {
    const groups = [];
    let previous;
    for (const point of payload.points) {
      if (!groups.length || point[4] !== previous) groups.push([]);
      groups.at(-1).push([point[0], point[1]]);
      previous = point[4];
    }
    return groups;
  }

  function mount(container, payload, imperial, status) {
    const L = window.L, config = window.ArchiveMapConfig;
    if (!L || !config) throw new Error('The local map library could not be loaded.');
    if (payload.points.length < 2) throw new Error('This recording has no usable GPS route.');
    const coordinates = payload.points.map(point => [point[0], point[1]]);
    const bounds = L.latLngBounds(coordinates);
    const map = L.map(container, {
      scrollWheelZoom: false,
      minZoom: 1,
      maxZoom: config.maxZoom,
      zoomAnimation: false,
      fadeAnimation: false,
    });
    let observer, disposed = false, loaded = 0, failed = 0;
    const updateStatus = () => {
      status.hidden = failed === 0;
      status.textContent = loaded
        ? 'Some map imagery could not load. The recorded route remains visible.'
        : 'Map imagery is unavailable. Connect to the internet for roads and place names; the recorded route remains visible.';
    };
    const tiles = L.tileLayer(config.tileUrl, {
      attribution: config.attribution,
      maxZoom: config.maxZoom,
      keepBuffer: 1,
      updateWhenIdle: true,
      referrerPolicy: 'strict-origin-when-cross-origin',
    });
    tiles.on('loading', () => { loaded = 0; failed = 0; status.hidden = true; });
    tiles.on('tileload', () => { loaded += 1; updateStatus(); });
    tiles.on('tileerror', () => { failed += 1; updateStatus(); });
    const fit = () => {
      if (disposed) return;
      map.invalidateSize({pan: false});
      map.fitBounds(bounds, {padding: [28, 28], maxZoom: config.fitMaxZoom, animate: false});
    };
    const destroy = () => {
      if (disposed) return;
      disposed = true;
      observer?.disconnect();
      map.remove();
    };
    try {
      const route = segments(payload);
      L.polyline(route, {color: '#fff', weight: 7, opacity: 0.9, smoothFactor: 0, interactive: false}).addTo(map);
      L.polyline(route, {color: '#0866bd', weight: 3.5, opacity: 1, smoothFactor: 0, interactive: false}).addTo(map);
      for (const [coordinate, label, color] of [
        [coordinates[0], 'Start', '#198148'],
        [coordinates.at(-1), 'Finish', '#d64400'],
      ]) {
        L.circleMarker(coordinate, {radius: label === 'Start' ? 7 : 4, color: '#fff', weight: 2, fillColor: color, fillOpacity: 1})
          .addTo(map).bindTooltip(label, {direction: 'top'});
      }
      L.control.scale({metric: !imperial, imperial, position: 'bottomleft'}).addTo(map);
      fit();
      tiles.addTo(map);
      if (typeof ResizeObserver !== 'undefined') {
        observer = new ResizeObserver(fit);
        observer.observe(container);
      }
      return {fit, destroy};
    } catch (error) {
      destroy();
      throw error;
    }
  }

  function show(container, payload, imperial) {
    container.innerHTML = '<div class="route-map" role="region" aria-label="Map of the recorded ride"></div>' +
      '<p class="map-status small muted" role="status" hidden></p>' +
      '<div class="route-map-actions"><button type="button" class="button fit-ride">Fit ride</button><a class="larger-map" target="_blank" rel="noopener noreferrer">View larger map ↗</a></div>' +
      '<div class="route-elevation"></div>';
    container.querySelector('.route-elevation').innerHTML = window.ArchiveRoute.profile(payload, imperial);
    try {
      const view = mount(container.querySelector('.route-map'), payload, imperial, container.querySelector('.map-status'));
      container.querySelector('.fit-ride').addEventListener('click', view.fit);
      const points = payload.points;
      const latitude = points.reduce((sum, point) => sum + point[0], 0) / points.length;
      const longitude = points.reduce((sum, point) => sum + point[1], 0) / points.length;
      container.querySelector('.larger-map').href = `https://www.openstreetmap.org/?mlat=${points[0][0]}&mlon=${points[0][1]}#map=12/${latitude}/${longitude}`;
      return view;
    } catch (error) {
      container.innerHTML = '<p class="small muted" role="status">Map unavailable. The recorded trace is shown below.</p><div class="route-static">' + window.ArchiveRoute.draw(payload, imperial) + '</div>';
      return {destroy() {}};
    }
  }

  return {segments, mount, show};
})();
