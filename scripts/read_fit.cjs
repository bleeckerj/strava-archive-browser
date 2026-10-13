const fs = require('node:fs');
const FitParser = require('fit-file-parser').default;
const input = JSON.parse(fs.readFileSync(0, 'utf8'));
const parser = new FitParser({force: false, mode: 'list', lengthUnit: 'm', speedUnit: 'm/s', temperatureUnit: 'celsius'});
parser.parse(Buffer.from(input.bytes, 'base64'), (error, data) => {
  if (error) { process.stdout.write(JSON.stringify({error: String(error)})); return; }
  const records = data.records || [];
  const stops=(data.events||[]).filter(e=>e.event==='timer'&&String(e.event_type).startsWith('stop')).map(e=>+e.timestamp);
  const sessions=(data.sessions||[]).map(s=>+s.start_time).filter(Number.isFinite);
  const boundaries=[...stops,...sessions].sort((a,b)=>a-b);
  const points=[];let segment=0,boundary=0;
  for(const r of records){
    if(!Number.isFinite(r.position_lat)||!Number.isFinite(r.position_long)||Math.abs(r.position_lat)>90||Math.abs(r.position_long)>180){segment++;continue;}
    const timestamp=r.timestamp instanceof Date?+r.timestamp:null;
    if(timestamp!==null){while(boundary<boundaries.length&&boundaries[boundary]<=timestamp){segment++;boundary++;}}
    points.push([r.position_lat,r.position_long,r.timestamp instanceof Date?r.timestamp.toISOString():null,
      Number.isFinite(r.enhanced_altitude)?r.enhanced_altitude:Number.isFinite(r.altitude)?r.altitude:null,segment]);
  }
  process.stdout.write(JSON.stringify({points, records: records.length}));
});
