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
}

echo "</pre>";

// Display the return status
echo "<strong>Return status:</strong> $return_var";
?>