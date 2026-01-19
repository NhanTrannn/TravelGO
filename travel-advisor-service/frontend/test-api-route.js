// Test fpt-planner API route directly with minimal payload
const https = require('http');

const data = JSON.stringify({
  messages: [
    { role: "user", content: "Tôi muốn đi Đà Lạt" }
  ]
});

const options = {
  hostname: 'localhost',
  port: 3000,
  path: '/api/fpt-planner',
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Content-Length': data.length
  }
};

console.log('🧪 Testing /api/fpt-planner...\n');

const req = https.request(options, (res) => {
  let body = '';

  res.on('data', (chunk) => {
    body += chunk;
  });

  res.on('end', () => {
    console.log(`Status: ${res.statusCode}`);
    
    if (res.statusCode === 200) {
      const json = JSON.parse(body);
      console.log('\n✅ SUCCESS!');
      console.log('Reply:', json.reply);
      console.log('UI Type:', json.ui_type);
      
      if (json.ui_data?.hotels) {
        console.log(`\n🏨 Hotels: ${json.ui_data.hotels.length}`);
        json.ui_data.hotels.slice(0, 3).forEach(h => {
          console.log(`   - ${h.name} (${h.priceRange})`);
        });
      }
    } else {
      console.log('\n❌ ERROR:', res.statusCode);
      console.log('Body:', body);
    }
  });
});

req.on('error', (error) => {
  console.error('❌ Request failed:', error.message);
});

req.write(data);
req.end();
