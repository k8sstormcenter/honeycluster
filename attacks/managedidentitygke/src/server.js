import { KeyManagementServiceClient } from '@google-cloud/kms';

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



async function main() {
    // The plaintext to be encrypted
    const plaintext = 'This is a secret message';

    // Construct the key name
    const name = client.cryptoKeyPath(projectId, locationId, keyRingId, keyName);
    console.log(`Using crypto key: ${name}`);

    // Convert the plaintext into bytes
    const plaintextBuffer = Buffer.from(plaintext);

    getKey().catch(console.error);
    // Encrypt the plaintext
    const [result] = await client.encrypt({
        name: name,
        plaintext: plaintextBuffer,
    });

    console.log(`Ciphertext: ${result.ciphertext.toString('base64')}`);
}

main().catch(console.error);