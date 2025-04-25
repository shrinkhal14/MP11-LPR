document.addEventListener('DOMContentLoaded', function() {
    // Handle real-time camera detection
    const video = document.getElementById('video');
    const canvas = document.getElementById('canvas');
    const captureBtn = document.getElementById('captureBtn');

    // Request access to the user's camera
    navigator.mediaDevices.getUserMedia({ video: true })
        .then((stream) => {
            video.srcObject = stream;
        })
        .catch((err) => {
            console.error('Error accessing the camera:', err);
        });

    // Capture the current frame and send for detection
    captureBtn.addEventListener('click', function() {
        const context = canvas.getContext('2d');
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        context.drawImage(video, 0, 0, canvas.width, canvas.height);
        
        // Convert the canvas image to a data URL and send it for recognition
        const imageData = canvas.toDataURL('image/png');
        console.log('Sending image data:', imageData);  // Debug: Log image data
        detectLicensePlate(imageData);
    });

    // Function to handle license plate detection
    function detectLicensePlate(imageData) {
        fetch('/process_image', {
            method: 'POST',
            body: JSON.stringify({ image: imageData }),
            headers: {
                'Content-Type': 'application/json'
            }
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            console.log('Response data:', data); // Debugging Output
    
            if (data.result && data.authorization) {
                let plateNumber = Array.isArray(data.result) ? data.result.join(', ') : data.result;

                let status = data.authorization; // 'Authorized Vehicle' or 'Unauthorized Vehicle'
                let message = `Detected Plate Number: ${plateNumber}\nAuthorization: ${status}`;
    
                // Show an alert with plate number and authorization status
                alert(message);
    
                // Update the result section in HTML
                document.getElementById('result').innerHTML = `
                    <p><strong>Detected Plate:</strong> ${plateNumber}</p>
                    <p><strong>Authorization:</strong> <span style="color: ${status === 'Authorized Vehicle' ? 'green' : 'red'}">${status}</span></p>
                `;
            } else if (data.error) {
                alert('Error: ' + data.error);
                document.getElementById('result').innerText = `Error: ${data.error}`;
            } else {
                alert('No plates detected.');
                document.getElementById('result').innerText = 'No plates detected.';
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Error processing the image.');
            document.getElementById('result').innerText = 'Error processing the image.';
        });
    }
    

    // Handle login form submission
    document.getElementById('loginForm')?.addEventListener('submit', function(event) {
        event.preventDefault();
        const email = document.getElementById('loginEmail').value;
        const password = document.getElementById('loginPassword').value;
        console.log('Login submitted with email:', email);
    });

    // Handle contact form submission
    document.getElementById('contactForm')?.addEventListener('submit', function(event) {
        event.preventDefault();
        const message = document.getElementById('contactMessage').value;
        console.log('Contact form submitted with message:', message);
    });

    // Handle sign-up form submission
    document.getElementById('signupForm')?.addEventListener('submit', function(event) {
        event.preventDefault();
        const email = document.getElementById('signupEmail').value;
        const password = document.getElementById('signupPassword').value;
        const username = document.getElementById('signupUsername').value;
        console.log('Sign-up submitted with email:', email, 'username:', username);
    });
});
