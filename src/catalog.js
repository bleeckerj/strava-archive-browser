(() => {
  'use strict';
  const {activities,meta}=window.STRAVA_ARCHIVE,U=window.ArchiveUtils,$=id=>document.getElementById(id);
  const {esc,num,duration,distance,elevation,speed,sum,fileUrl}=U;
  document.getElementById('archive-zip').href='data/'+encodeURIComponent(meta.sourceArchive);
  const filters=['search','year','type','gear','format','from','through'];
  let imperial=false,sort='utc',direction=-1,page=1,pageSize=50,view='activities',filtered=[...activities];
  const byId=new Map(activities.map(a=>[a.id,a]));
  $('coverage').textContent=`${activities.length.toLocaleString()} activities · ${activities.at(-1).localDate} to ${activities[0].localDate} · ${meta.files.toLocaleString()} activity files`;
  $('timezone-label').textContent=meta.timezone;
  for(const [id,key] of [['year','year'],['type','type'],['gear','gear']]){
    const options=[...new Set(activities.map(a=>a[key]))].sort((a,b)=>id==='year'?b-a:String(a).localeCompare(String(b)));
    for(const value of options){const option=document.createElement('option');option.value=value===''?'__none':value;option.textContent=value===''?'Not recorded':value;$(id).append(option);}
  }
  function applyFilters(){
    const query=$('search').value.trim().toLocaleLowerCase(),year=$('year').value,type=$('type').value,gear=$('gear').value,format=$('format').value;
    filtered=activities.filter(a=>(!query||[a.name,a.description,a.note,a.gear,a.id].some(v=>String(v??'').toLocaleLowerCase().includes(query)))&&(!year||String(a.year)===year)&&(!type||a.type===type)&&(!gear||(gear==='__none'?!a.gear:a.gear===gear))&&(!format||(format==='missing'?!a.file:a.format===format))&&(!$('from').value||a.localDate>=$('from').value)&&(!$('through').value||a.localDate<=$('through').value));
    page=1;render();
  }
  function sortItems(){return [...filtered].sort((a,b)=>{const av=a[sort],bv=b[sort];if(av===null||av===undefined)return bv===null||bv===undefined?0:1;if(bv===null||bv===undefined)return -1;return typeof av==='number'?(av-bv)*direction:String(av).localeCompare(String(bv))*direction;});}
  function show(id){const item=byId.get(String(id));if(item)window.ArchiveDetail.show(item,imperial);}
  function renderStats(){
    const values=[['ACTIVITIES',num(filtered.length,0),''],['DISTANCE',distance(sum(filtered,'distance'),imperial),imperial?'mi':'km'],['MOVING TIME',num(sum(filtered,'moving')/3600,1),'hours'],['ELEVATION GAIN',elevation(sum(filtered,'elevation'),imperial),imperial?'ft':'m'],['ACTIVITY FILES',num(filtered.filter(a=>a.file).length,0),'']];
    $('stats').innerHTML=values.map(([label,value,suffix])=>`<div class="stat"><span class="label">${label}</span><span class="value">${value}</span><span class="suffix">${suffix}</span></div>`).join('');
  }
  function renderTable(){
    const ordered=sortItems(),pages=Math.max(1,Math.ceil(ordered.length/pageSize));page=Math.min(page,pages);
    const rows=ordered.slice((page-1)*pageSize,page*pageSize);
    $('activity-rows').innerHTML=rows.length?rows.map(a=>`<tr><td>${a.localDate}<span class="subline">${a.localTime} ${a.localZone}</span></td><td><button class="activity-name" data-id="${esc(a.id)}">${esc(a.name)}</button><span class="subline">${esc(a.type)} · ${esc(a.id)}</span></td><td>${esc(a.gear)||'<span class="muted">Not recorded</span>'}</td><td class="numeric">${distance(a.distance,imperial)}<span class="subline">${imperial?'mi':'km'}</span></td><td class="numeric">${duration(a.moving)}</td><td class="numeric">${elevation(a.elevation,imperial)}<span class="subline">${imperial?'ft':'m'}</span></td><td class="numeric"><span ${a.speedDerived?'class="derived" title="Calculated: distance divided by moving time"':''}>${speed(a.speed,imperial)}</span><span class="subline">${imperial?'mph':'km/h'}</span></td><td>${a.file?`<a class="file-link" href="${fileUrl(a.file)}" download>${a.format}</a>`:'<span class="missing">No file</span>'}</td></tr>`).join(''):'<tr><td colspan="8" class="empty">No activities match these filters.</td></tr>';
    $('activity-rows').querySelectorAll('[data-id]').forEach(button=>button.addEventListener('click',()=>show(button.dataset.id)));
    $('result-count').textContent=`${filtered.length.toLocaleString()} of ${activities.length.toLocaleString()} activities · ${imperial?'Miles, feet, and mph':'Kilometres, metres, and km/h'} · Dates in ${meta.timezone}`;
    $('page-info').textContent=`Page ${page} of ${pages} · ${ordered.length?((page-1)*pageSize+1).toLocaleString():0}–${Math.min(page*pageSize,ordered.length).toLocaleString()}`;
    $('previous').disabled=page===1;$('next').disabled=page===pages;
    document.querySelectorAll('[data-sort]').forEach(button=>{button.querySelector('span').textContent=sort===button.dataset.sort?(direction===1?'↑':'↓'):'';button.closest('th').setAttribute('aria-sort',sort===button.dataset.sort?(direction===1?'ascending':'descending'):'none');});
  }
  function groupedTable(key){
    const groups=new Map();for(const a of filtered){const value=a[key]||'Not recorded';if(!groups.has(value))groups.set(value,[]);groups.get(value).push(a);}
    const groupsSorted=[...groups.entries()].sort((a,b)=>key==='year'?b[0]-a[0]:sum(b[1],'distance')-sum(a[1],'distance'));
    const header=`<tr><th>${key==='year'?'Year':'Gear'}</th><th class="numeric">Activities</th><th class="numeric">Distance (${imperial?'mi':'km'})</th><th class="numeric">Moving hours</th><th class="numeric">Elapsed hours</th><th class="numeric">Elevation (${imperial?'ft':'m'})</th><th class="numeric">Mean distance</th></tr>`;
    const rows=groupsSorted.map(([group,items])=>`<tr><td><button class="activity-name" data-group="${esc(group)}">${esc(group)}</button></td><td class="numeric">${num(items.length,0)}</td><td class="numeric">${distance(sum(items,'distance'),imperial)}</td><td class="numeric">${num(sum(items,'moving')/3600)}</td><td class="numeric">${num(sum(items,'elapsed')/3600)}</td><td class="numeric">${elevation(sum(items,'elevation'),imperial)}</td><td class="numeric">${distance(sum(items,'distance')/Math.max(1,items.filter(a=>a.distance!==null).length),imperial)}</td></tr>`).join('');
    return `<table><thead>${header}</thead><tbody>${rows||'<tr><td colspan="7" class="empty">No activities match these filters.</td></tr>'}</tbody></table>`;
  }
  function renderTotals(){
    for(const [target,key] of [['year-totals','year'],['gear-totals','gear']]){
      $(target).innerHTML=groupedTable(key);$(target).querySelectorAll('[data-group]').forEach(button=>button.addEventListener('click',()=>{$(key).value=button.dataset.group==='Not recorded'?'__none':button.dataset.group;setView('activities');applyFilters();}));
    }
  }
  function render(){renderStats();renderTable();renderTotals();if(view==='activities'){window.ArchiveCharts.yearly(filtered,$('year-metric').value,imperial,year=>{$('year').value=year;applyFilters();});window.ArchiveCharts.scatter(filtered,imperial,show);}}
  function setView(next){view=next;for(const name of ['activities','totals','notes'])$(name+'-view').hidden=name!==next;document.querySelectorAll('[data-view]').forEach(button=>button.setAttribute('aria-pressed',String(button.dataset.view===next)));render();}
  filters.forEach(id=>$(id).addEventListener(id==='search'?'input':'change',applyFilters));
  $('clear').addEventListener('click',()=>{filters.forEach(id=>$(id).value='');applyFilters();});
  document.querySelectorAll('[data-sort]').forEach(button=>button.addEventListener('click',()=>{if(sort===button.dataset.sort)direction*=-1;else{sort=button.dataset.sort;direction=['name','gear'].includes(sort)?1:-1;}page=1;renderTable();}));
  document.querySelectorAll('[data-view]').forEach(button=>button.addEventListener('click',()=>setView(button.dataset.view)));
  for(const [id,value] of [['metric',false],['imperial',true]])$(id).addEventListener('click',()=>{imperial=value;$('metric').setAttribute('aria-pressed',String(!imperial));$('imperial').setAttribute('aria-pressed',String(imperial));render();});
  $('previous').addEventListener('click',()=>{page--;renderTable();});$('next').addEventListener('click',()=>{page++;renderTable();});
  $('page-size').addEventListener('change',()=>{pageSize=Number($('page-size').value);page=1;renderTable();});
  $('year-metric').addEventListener('change',render);$('export-filtered').addEventListener('click',()=>U.exportCsv(sortItems()));
  $('close-detail').addEventListener('click',()=>$('activity-detail').close());$('activity-detail').addEventListener('click',e=>{if(e.target===$('activity-detail')){const r=e.target.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)e.target.close();}});
  $('archive-notes').innerHTML=`<dl class="source-facts"><dt>Source archive</dt><dd>${esc(meta.sourceArchive)}</dd><dt>Activity coverage</dt><dd>${activities.at(-1).localDate} to ${activities[0].localDate}</dd><dt>Records / files</dt><dd>${meta.records.toLocaleString()} / ${meta.files.toLocaleString()}</dd><dt>File formats</dt><dd>${Object.entries(meta.formats).map(([type,count])=>`${count.toLocaleString()} ${type}`).join(' · ')}</dd><dt>Displayed timezone</dt><dd>${esc(meta.timezone)}</dd><dt>Archive SHA-256</dt><dd><code>${esc(meta.sourceSha256)}</code></dd></dl>`;
  $('calculation-notes').innerHTML=meta.notes.map(note=>`<li>${esc(note)}</li>`).join('');
  $('missing-files').innerHTML=meta.noFileIds.map(id=>{const a=byId.get(id);return `<p>${a.localDate} · <button class="activity-name" data-id="${a.id}">${esc(a.name)}</button> · ${a.id}</p>`;}).join('')||'<p>Every activity has an associated file.</p>';
  $('missing-files').querySelectorAll('[data-id]').forEach(button=>button.addEventListener('click',()=>show(button.dataset.id)));
  $('preview-coverage').innerHTML=`<p>${meta.previews.toLocaleString()} activities have recorded route previews. ${meta.previewErrors.length.toLocaleString()} files have a parsing issue; the original files remain available.</p>`+(meta.previewErrors.length?`<details><summary>Preview parsing issues</summary>${meta.previewErrors.map(issue=>`<p>${esc(issue.activityId)} · ${esc(issue.error)}</p>`).join('')}</details>`:'')+`<p>FIT files are also available as readable .fit copies. To use FIT Preview, select one in Finder and press the space bar.</p>`;
  render();
})();
