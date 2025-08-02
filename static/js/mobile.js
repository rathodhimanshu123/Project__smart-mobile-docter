document.addEventListener('DOMContentLoaded', async () => {
    const status = document.getElementById('status');
    const collectedData = document.getElementById('collected-data');
    const dataList = document.getElementById('data-list');
    const sendDataBtn = document.getElementById('send-data');

    // Add scanning animation
    status.classList.add('scanning');

    // Collect phone data
    const phoneData = {
        userAgent: navigator.userAgent,
        platform: navigator.platform,
        language: navigator.language,
        screenResolution: `${window.screen.width}x${window.screen.height}`,
        screenColorDepth: window.screen.colorDepth,
        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
        connection: navigator.connection ? {
            type: navigator.connection.effectiveType,
            downlink: navigator.connection.downlink,
            rtt: navigator.connection.rtt
        } : 'Not available',
        deviceMemory: navigator.deviceMemory || 'Not available',
        hardwareConcurrency: navigator.hardwareConcurrency || 'Not available'
    };

    // Display collected data
    status.classList.remove('scanning');
    status.textContent = 'Data collected successfully!';
    status.classList.add('success');
    
    collectedData.classList.remove('hidden');
    
    // Populate data list
    for (const [key, value] of Object.entries(phoneData)) {
        const li = document.createElement('li');
        if (typeof value === 'object' && value !== null) {
            li.innerHTML = `<strong>${formatKey(key)}:</strong> ${JSON.stringify(value)}`;
        } else {
            li.innerHTML = `<strong>${formatKey(key)}:</strong> ${value}`;
        }
        dataList.appendChild(li);
    }

    // Handle data submission
    sendDataBtn.addEventListener('click', async () => {
        try {
            status.textContent = 'Sending data...';
            status.classList.add('scanning');
            
            const response = await fetch('/api/submit_phone_data', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    session_id: sessionId,
                    phone_data: phoneData
                })
            });

            const result = await response.json();
            
            if (result.success) {
                status.textContent = 'Data sent successfully! You can close this page.';
                status.classList.remove('scanning');
                status.classList.add('success');
                sendDataBtn.disabled = true;
            } else {
                throw new Error('Failed to send data');
            }
        } catch (error) {
            console.error('Error sending data:', error);
            status.textContent = 'Error sending data. Please try again.';
            status.classList.remove('scanning');
            status.classList.add('error');
        }
    });
});

// Helper function to format key names
function formatKey(key) {
    return key
        .replace(/([A-Z])/g, ' $1') // Add space before capital letters
        .replace(/^./, str => str.toUpperCase()) // Capitalize first letter
        .replace(/([A-Z])/g, str => str.toLowerCase()); // Convert remaining to lowercase
}
