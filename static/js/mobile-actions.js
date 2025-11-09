// Handle saving and downloading device information
document.addEventListener('DOMContentLoaded', function() {
    const saveLogBtn = document.getElementById('save-log-btn');
    const statusMessage = document.getElementById('status-message');
    
    if (saveLogBtn) {
        saveLogBtn.addEventListener('click', async function() {
            try {
                // Show loading state
                saveLogBtn.textContent = '⏳ Saving...';
                saveLogBtn.disabled = true;
                statusMessage.textContent = 'Generating log file...';

                // Get all device information from the displayed data
                const deviceInfo = {};
                const dataItems = document.querySelectorAll('.data-item');
                dataItems.forEach(item => {
                    const label = item.querySelector('strong').textContent.replace(':', '');
                    const value = item.querySelector('.value').textContent;
                    deviceInfo[label] = value;
                });

                // Add session ID
                deviceInfo.sessionId = document.body.dataset.sessionId;

                // Send data to server
                const response = await fetch('/collect_device_info', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(deviceInfo)
                });

                if (!response.ok) {
                    throw new Error('Failed to generate log file');
                }

                const result = await response.json();
                
                if (result.log_file) {
                    // Trigger download
                    const downloadResponse = await fetch(`/download_log/${result.log_file}`);
                    if (!downloadResponse.ok) {
                        throw new Error('Failed to download log file');
                    }

                    const blob = await downloadResponse.blob();
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.style.display = 'none';
                    a.href = url;
                    a.download = result.log_file;
                    document.body.appendChild(a);
                    a.click();
                    window.URL.revokeObjectURL(url);
                    document.body.removeChild(a);

                    // Show success message
                    statusMessage.textContent = 'Log file saved successfully!';
                    saveLogBtn.textContent = '✅ Saved! Tap to save again';
                }
            } catch (error) {
                console.error('Error saving log file:', error);
                statusMessage.textContent = 'Failed to save log file. Please try again.';
                saveLogBtn.textContent = '❌ Failed - Tap to retry';
            } finally {
                saveLogBtn.disabled = false;
            }
        });
    }
});
