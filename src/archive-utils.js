window.ArchiveUtils = (() => {
  const esc=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const num=(value,decimals=1)=>value===null||value===undefined?'—':Number(value).toLocaleString(undefined,{minimumFractionDigits:decimals,maximumFractionDigits:decimals});
  const duration=seconds=>{if(seconds===null||seconds===undefined)return '—';const mins=Math.floor(seconds/60);return `${Math.floor(mins/60)}h ${String(mins%60).padStart(2,'0')}m`;};
  const distance=(metres,imperial)=>num(metres===null?null:metres/(imperial?1609.344:1000));
  const elevation=(metres,imperial)=>num(metres===null?null:metres*(imperial?3.280839895:1),0);
  const speed=(value,imperial)=>num(value===null?null:value*(imperial?2.236936292:3.6));
  const sum=(items,key)=>items.reduce((total,item)=>total+(item[key]??0),0);
  const fileUrl=path=>'data/catalog/'+path.split('/').map(encodeURIComponent).join('/');
  const safeCsv=value=>{let text=String(value??'');if(typeof value==='string'&&/^[=+@-]/.test(text))text="'"+text;return '"'+text.replace(/"/g,'""')+'"';};
  function exportCsv(items){
    const columns=['Activity ID','Activity name','Activity type','Start UTC','Date America/Los_Angeles','Gear','Distance km','Distance miles','Moving seconds','Elapsed seconds','Elevation gain m','Average speed km/h','Average speed derived','Average heart rate bpm','Average watts','Format','File'];
    const rows=items.map(a=>[a.id,a.name,a.type,a.utc,a.localDate+' '+a.localTime+' '+a.localZone,a.gear,a.distance===null?'':a.distance/1000,a.distance===null?'':a.distance/1609.344,a.moving,a.elapsed,a.elevation,a.speed===null?'':a.speed*3.6,a.speedDerived,a.heartRate,a.power,a.format,a.file]);
    const content='\ufeff'+[columns,...rows].map(row=>row.map(safeCsv).join(',')).join('\r\n');
    const url=URL.createObjectURL(new Blob([content],{type:'text/csv;charset=utf-8;'}));const link=document.createElement('a');link.href=url;link.download='Strava-activities-filtered.csv';document.body.append(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);
  }
  return {esc,num,duration,distance,elevation,speed,sum,fileUrl,exportCsv};
})();
