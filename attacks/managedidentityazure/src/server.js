import * as msal from "@azure/msal-node";
import fs from "fs";
import { SecretClient } from "@azure/keyvault-secrets";
import express from 'express';
class MyClientAssertionCredential {
    constructor() {
        let clientAssertion = ""
        try {
            clientAssertion = fs.readFileSync(process.env.AZURE_FEDERATED_TOKEN_FILE, "utf8")
        } catch (err) {
            console.log("Failed to read client assertion file: " + err)
            process.exit(1)
        }

        this.app = new msal.ConfidentialClientApplication({
            auth: {
                clientId: process.env.AZURE_CLIENT_ID,
                authority: `${process.env.AZURE_AUTHORITY_HOST}${process.env.AZURE_TENANT_ID}`,
                clientAssertion: clientAssertion,
            }
        })
    }

    async getToken(scopes) {
        const token = await this.app.acquireTokenByClientCredential({ scopes: ['https://vault.azure.net/.default'] }).catch(error => console.log(error))
        return new Promise((resolve, reject) => {
            if (token) {
                resolve({
                    token: token.accessToken,
                    expiresOnTimestamp: token.expiresOn.getTime(),
                })
            } else {
                reject(new Error("Failed to get token silently"))
            }
        })
    }
}
const app = express();
const port = 8080;

// Vulnerable Endpoint 1: SQL Injection (Simulation)
app.get('/vulnerable/sql-injection', (req, res) => {
    const simulatedUserInput = req.query.username; // Never directly use user input in queries!
    const simulatedQuery = `SELECT * FROM users WHERE username = '${simulatedUserInput}'`; 
  
    console.log("Simulated Vulnerable Query:", simulatedQuery); // Log for demonstration
    res.send("This endpoint simulates a SQL injection vulnerability. Check the logs!");
  });
  
  // Vulnerable Endpoint 2: Cross-Site Scripting (XSS) (Simulation)
  app.get('/vulnerable/xss', (req, res) => {
    const simulatedUserInput = req.query.input; // Never directly reflect user input!
    res.send(`<p>You entered: ${simulatedUserInput}</p>`); 
  });
  
  // Vulnerable Endpoint 3: Accessing Environment Variables (Simulation)
  app.get('/vulnerable/env', (req, res) => {
    // In a real vulnerability, an attacker might manipulate this to access sensitive data
    const envVar = req.query.varName;
    const value = process.env[envVar]; 
    res.send(`Value of ${envVar}: ${value}`);
  });

  // Simulated vulnerable logging library (insecurely logs object properties)
function vulnerableLog(obj) {
    // In a real vulnerability, this might iterate over object properties 
    // without proper sanitization or access control.
    console.log("Logging object:", obj); 
  }
  
  // Vulnerable Endpoint: Exploiting the vulnerable logging function
app.get('/vulnerable/log-injection', (req, res) => {
    const userInput = req.query.data;
  
    // Construct an object where user input is used as a property name
    const dataToLog = {
      message: "Some information",
      [userInput]: "User-controlled data" // Vulnerable: User input as property name
    };
  
    vulnerableLog(dataToLog); 
    res.send("Data logged. Check the server logs.");
  });
  
  app.listen(port, () => {
    console.log(`Server listening on port ${port}`);
  });
const main = async () => {
    // create a token credential object, which has a getToken method that returns a token
    const tokenCredential = new MyClientAssertionCredential()

    const keyvaultURL = process.env.KEYVAULT_URL
    if (!keyvaultURL) {
        throw new Error("KEYVAULT_URL environment variable not set")
    }
    const secretName = process.env.SECRET_NAME
    if (!secretName) {
        throw new Error("SECRET_NAME environment variable not set")
    }

    // create a secret client with the token credential
    const keyvault = new SecretClient(keyvaultURL, tokenCredential)
    console.log(`successfully created secret client, keyvaultURL=${keyvaultURL}, secretName=${secretName}`)
    console.log(`getting secret, Name=${tokenCredential}`)
    const secret = await keyvault.getSecret(secretName).catch(error => console.log(error))
    console.log(`Secret object: ${JSON.stringify(secret, null, 2)}`);
    if (secret) {
      console.log(`Successfully got secret, secret value=${secret.value}`);
    } else {
      console.log('Failed to get secret, secret object is null or undefined');
    }
}

main()