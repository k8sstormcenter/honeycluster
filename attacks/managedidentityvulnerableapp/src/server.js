import express from 'express';
import path from 'path';
import { fileURLToPath } from 'url';
import { execSync } from 'child_process';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
const port = 8080;

// Vulnerable Endpoint 1: Accessing Environment Variables (Simulation)
app.get('/env', (req, res) => {
  const envVar = req.query.name;
  const value = process.env[envVar]; 
  res.send(value);
});

// Vulnerable Endpoint 2: Path Traversal (Simulation)
app.get('/file', (req, res) => {
  const file = req.query.name;
  const value = fs.readFileSync(path.join(__dirname, file));
  res.send(value);
});

// Vulnerable Endpoint 3: RCE (Simulation)
app.get('/cat', (req, res) => {
  const file = req.query.name;
  const value = execSync(`cat ${file}`).toString();
  res.send(value);
});

app.listen(port, () => {
  console.log(`Server listening on port ${port}`);
});
