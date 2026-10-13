window.STRAVA_TRACKS = Object.create(null);
window.ArchiveRoute = (() => {
  function load(item) {
    if(window.STRAVA_TRACKS[item.id]) return Promise.resolve(window.STRAVA_TRACKS[item.id]);
    return new Promise((resolve,reject)=>{const script=document.createElement('script');script.src=window.ArchiveUtils.fileUrl(item.preview);script.onload=()=>resolve(window.STRAVA_TRACKS[item.id]);script.onerror=()=>reject(new Error('The local route preview could not be loaded.'));document.head.append(script);});
  }
  function draw(payload,imperial) {
    const points=payload.points;
    const w=760,h=330,pad=27;
    const origin=points[0][1];
    const project=p=>{let longitude=p[1]-origin;while(longitude>180)longitude-=360;while(longitude< -180)longitude+=360;const latitude=Math.min(89.9,Math.max(-89.9,p[0]))*Math.PI/180;return [longitude*Math.PI/180,-Math.log(Math.tan(Math.PI/4+latitude/2))];};
    const xy=points.map(project),xs=xy.map(p=>p[0]),ys=xy.map(p=>p[1]);
    const minX=Math.min(...xs),maxX=Math.max(...xs),minY=Math.min(...ys),maxY=Math.max(...ys);
    const scale=Math.min((w-2*pad)/Math.max(maxX-minX,1e-8),(h-2*pad)/Math.max(maxY-minY,1e-8));
    const xOffset=(w-(maxX-minX)*scale)/2,yOffset=(h-(maxY-minY)*scale)/2;
    const coords=xy.map(p=>[(p[0]-minX)*scale+xOffset,(p[1]-minY)*scale+yOffset]);
    const route=coords.map((p,i)=>`${i&&points[i][4]===points[i-1][4]?'L':'M'}${p[0].toFixed(2)},${p[1].toFixed(2)}`).join(' '),first=coords[0],last=coords[coords.length-1];
    let html=`<svg viewBox="0 0 ${w} ${h}" role="img" aria-label="Recorded route, north at the top"><path d="${route}" fill="none" stroke="#0866bd" stroke-width="2.4" stroke-linejoin="round" stroke-linecap="round"/><circle cx="${first[0]}" cy="${first[1]}" r="5" fill="#198148" stroke="#fff" stroke-width="2"/><circle cx="${last[0]}" cy="${last[1]}" r="5" fill="#d64400" stroke="#fff" stroke-width="2"/><text x="${w-22}" y="21" text-anchor="middle" fill="#526171" font-size="11">N ↑</text></svg>`;
    html += profile(payload,imperial);
    return html;
  }
  function profile(payload,imperial) {
    const points=payload.points,w=760,pad=27;
    let html="";
    const elevation=points.map((p,i)=>[i,p[3]]).filter(p=>p[1]!==null&&Number.isFinite(p[1]));
    if(elevation.length>1){const factor=imperial?3.280839895:1,alts=elevation.map(p=>p[1]*factor),lo=Math.min(...alts),hi=Math.max(...alts),eh=95;
      const line=elevation.map((p,i)=>`${i?'L':'M'}${(pad+p[0]/Math.max(points.length-1,1)*(w-2*pad)).toFixed(1)},${(18+(hi-p[1]*factor)/Math.max(hi-lo,1)*(eh-35)).toFixed(1)}`).join(' ');
      html+=`<svg viewBox="0 0 ${w} ${eh}" role="img" aria-label="Recorded elevation profile"><line x1="${pad}" y1="${eh-16}" x2="${w-pad}" y2="${eh-16}" stroke="#dce2e8"/><path d="${line}" fill="none" stroke="#0866bd" stroke-width="1.7"/><text x="${pad}" y="12" fill="#526171" font-size="10">Elevation: ${Math.round(lo).toLocaleString()}–${Math.round(hi).toLocaleString()} ${imperial?'ft':'m'}</text><text x="${w-pad}" y="${eh-1}" text-anchor="end" fill="#526171" font-size="10">Progress through recorded GPS samples</text></svg>`;}
    return html;
  }
  return {load,draw,profile};
})();
