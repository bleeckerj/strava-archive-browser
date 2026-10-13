window.ArchiveCharts = (() => {
  const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const roundedMax = value => {if (!value) return 1; const order = 10 ** Math.floor(Math.log10(value)); return Math.ceil(value/order)*order;};
  function yearly(activities, metric, imperial, onSelect) {
    const groups = new Map();
    for (const a of activities) {if(!groups.has(a.year)) groups.set(a.year, []); groups.get(a.year).push(a);}
    const years = [...groups.keys()].sort((a,b)=>a-b);
    const values = years.map(year => metric==='count' ? groups.get(year).length : groups.get(year).reduce((s,a)=>s+(a[metric] ?? 0),0) / (metric==='moving' ? 3600 : imperial ? 1609.344 : 1000));
    const unit = metric==='count' ? 'activities' : metric==='moving' ? 'hours' : imperial ? 'mi' : 'km';
    const w=580,h=205,left=45,right=10,top=20,bottom=32,plotW=w-left-right,plotH=h-top-bottom;
    const max=roundedMax(Math.max(...values,0)), step=plotW/Math.max(years.length,1);
    let content=`<text x="${left}" y="10" class="chart-axis">${unit}</text>`;
    for(let i=0;i<=3;i++){const y=top+plotH*(1-i/3);content+=`<line x1="${left}" y1="${y}" x2="${w-right}" y2="${y}" stroke="#e1e7ed"/><text x="${left-7}" y="${y+3}" text-anchor="end" class="chart-axis">${Math.round(max*i/3).toLocaleString()}</text>`;}
    years.forEach((year,i)=>{const barH=values[i]/max*plotH,x=left+i*step+step*.15;content+=`<g class="year-choice" data-year="${year}" role="button" tabindex="0" aria-label="Filter to ${year}"><rect class="chart-bar" x="${x}" y="${top+plotH-barH}" width="${step*.7}" height="${Math.max(barH,1)}" rx="2"><title>${year}: ${values[i].toLocaleString(undefined,{maximumFractionDigits:1})} ${unit}; ${groups.get(year).length} activities</title></rect><text x="${left+(i+.5)*step}" y="${h-12}" text-anchor="middle" class="chart-axis">${year}</text></g>`;});
    const target=document.getElementById('year-chart');
    target.innerHTML=years.length?`<svg viewBox="0 0 ${w} ${h}" role="img" aria-label="${esc(unit)} by year">${content}</svg>`:'<p class="empty">No activities in this selection.</p>';
    target.querySelectorAll('[data-year]').forEach(node=>{node.addEventListener('click',()=>onSelect(node.dataset.year));node.addEventListener('keydown',e=>{if(['Enter',' '].includes(e.key)){e.preventDefault();onSelect(node.dataset.year);}});});
  }
  function scatter(activities, imperial, onSelect) {
    const items=activities.filter(a=>a.distance!==null&&a.elevation!==null);
    const w=580,h=205,left=53,right=14,top=18,bottom=36,plotW=w-left-right,plotH=h-top-bottom;
    const distances=items.map(a=>a.distance/(imperial?1609.344:1000)), elevations=items.map(a=>a.elevation*(imperial?3.280839895:1));
    const maxX=roundedMax(Math.max(...distances,0)),maxY=roundedMax(Math.max(...elevations,0));
    let content=`<text x="${left}" y="10" class="chart-axis">Elevation gain (${imperial?'ft':'m'})</text>`;
    for(let i=0;i<=3;i++){const x=left+plotW*i/3,y=top+plotH*(1-i/3);content+=`<line x1="${left}" y1="${y}" x2="${w-right}" y2="${y}" stroke="#e1e7ed"/><text x="${left-7}" y="${y+3}" text-anchor="end" class="chart-axis">${Math.round(maxY*i/3).toLocaleString()}</text><text x="${x}" y="${h-18}" text-anchor="middle" class="chart-axis">${Math.round(maxX*i/3)}</text>`;}
    content+=`<text x="${w-right}" y="${h-3}" text-anchor="end" class="chart-axis">Distance (${imperial?'mi':'km'})</text>`;
    items.forEach((a,i)=>{content+=`<circle class="chart-point" data-id="${esc(a.id)}" cx="${left+distances[i]/maxX*plotW}" cy="${top+plotH-elevations[i]/maxY*plotH}" r="3.4" role="button" tabindex="0" aria-label="${esc(a.name)}"><title>${esc(a.name)} · ${a.localDate} · ${distances[i].toFixed(1)} ${imperial?'mi':'km'} · ${Math.round(elevations[i]).toLocaleString()} ${imperial?'ft':'m'}</title></circle>`;});
    const target=document.getElementById('scatter-chart');target.innerHTML=items.length?`<svg viewBox="0 0 ${w} ${h}" role="img" aria-label="Activity distance versus elevation gain">${content}</svg>`:'<p class="empty">No recorded elevation in this selection.</p>';
    target.querySelectorAll('[data-id]').forEach(node=>{node.addEventListener('click',()=>onSelect(node.dataset.id));node.addEventListener('keydown',e=>{if(['Enter',' '].includes(e.key)){e.preventDefault();onSelect(node.dataset.id);}});});
  }
  return {yearly,scatter};
})();
