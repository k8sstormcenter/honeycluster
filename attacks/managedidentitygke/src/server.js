import { KeyManagementServiceClient } from '@google-cloud/kms';
import { GoogleAuth } from 'google-auth-library';

import express from 'express';
import path from 'path';
import { fileURLToPath } from 'url';
import { execSync } from 'child_process';
import fs from "fs";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
// Initialize the KMS client
const client = new KeyManagementServiceClient();

// Load values from environment variables
const projectId = process.env.KMS_PROJECT_ID;
const locationId = process.env.KMS_LOCATION;
const keyRingId = process.env.KMS_KEY_RING;
const keyName = process.env.KMS_KEY_NAME;

if (!projectId || !locationId || !keyRingId || !keyName) {
    throw new Error('Missing one or more required environment variables of: KMS_PROJECT_ID, KMS_LOCATION, KMS_KEY_RING, KMS_KEY_NAME');
}
async function getKey() {
    // Construct the key name
    const name = client.cryptoKeyPath(projectId, locationId, keyRingId, keyName);
    console.log(`Retrieving crypto key: ${name}`);

    // Retrieve the key
    const [key] = await client.getCryptoKey({ name });
    console.log('Crypto Key:', key);
}

const app = express();
const port = 8080;

// Vulnerable Endpoint 1: Accessing Environment Variables (Simulation)
app.get('/env', (req, res) => {
  const envVar = req.params.name;
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

async function getJwtToken() {
    const auth = new GoogleAuth({
        scopes: 'https://www.googleapis.com/auth/cloud-platform'
    });

    const client = await auth.getClient();
    const projectId = await auth.getProjectId();
    const url = `https://cloudkms.googleapis.com/v1/projects/${projectId}/locations/${locationId}/keyRings/${keyRingId}/cryptoKeys/${keyName}:encrypt`;

    const token = await client.getAccessToken();
    console.log('JWT Token:', token.token);
}
async function main() {
    // The plaintext to be encrypted
    // Print the JWT token
    await getJwtToken();
    const plaintext = 'This is a secret message';

    // Construct the key name
    const name = client.cryptoKeyPath(projectId, locationId, keyRingId, keyName);
    console.log(`Using crypto key: ${name}`);

    // Convert the plaintext into bytes
    const plaintextBuffer = Buffer.from(plaintext);

    // this will fail with the current IAM.rolebindings but helps figure out the token flow
    //getKey().catch(console.error);
    // Encrypt the plaintext
    const [result] = await client.encrypt({
        name: name,
        plaintext: plaintextBuffer,
    });

    console.log(`Ciphertext: ${result.ciphertext.toString('base64')}`);
}

main().catch(console.error);