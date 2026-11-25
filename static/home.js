 // Initialize the Leaflet map centered on Lebanon
    const map = L.map('map').setView([33.89, 35.50], 10);

    // Add OpenStreetMap tiles to display the map
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap contributors',
        maxZoom: 19
    }).addTo(map);

    // Create a layer to hold the roads displayed on the map
    const roadsLayer = L.featureGroup().addTo(map);

    // Create a separate layer to display reported potholes
    const potholesLayer = L.layerGroup().addTo(map);

    // Store the marker for the new pothole report location
let selectedLocationMarker = null;


function updateSelectedLocation(latitude, longitude) {

    // Save the coordinates in the reporting form
    document.getElementById('pothole-latitude').value = latitude;
    document.getElementById('pothole-longitude').value = longitude;

    // Update the visible confirmation message
    document.getElementById('selected-location-status').textContent =
        'Pothole location selected: ' +
        latitude.toFixed(6) + ', ' +
        longitude.toFixed(6);

    // Create the marker if it does not exist
    if (selectedLocationMarker === null) {

        selectedLocationMarker = L.marker(
            [latitude, longitude],
            { draggable: true }
        ).addTo(map);

        // Detect when the marker is dragged
        selectedLocationMarker.on('dragend', function(event) {

            const newPosition = event.target.getLatLng();

            updateSelectedLocation(
                newPosition.lat,
                newPosition.lng
            );

        });

    } else {

        // Move the marker if it already exists
        selectedLocationMarker.setLatLng([latitude, longitude]);

    }
}



 // Select a pothole location by clicking the map
map.on('click', function(event) {

    // Get the coordinates of the clicked location
    const latitude = event.latlng.lat;
    const longitude = event.latlng.lng;

    // Update the marker, hidden fields, and confirmation message
    updateSelectedLocation(latitude, longitude);

});


    // Display reported potholes as red circles on the map
    function displayPotholes(reports) {

        // Remove previously displayed potholes
        potholesLayer.clearLayers();

        // Go through each pothole report
        reports.forEach(function(report) {

            // Create a red circle at the reported location
            const potholeMarker = L.circleMarker(
                [report.latitude, report.longitude],
                {
                    color: 'red',
                    fillColor: 'red',
                    fillOpacity: 0.7,
                    radius: 7
                }
            );
            // Create a popup displaying the pothole information
const popup = document.createElement('div');

// Display the pothole report ID
const reportTitle = document.createElement('strong');
reportTitle.textContent = 'Pothole Report #' + report.id;

// Display the pothole severity
const severity = document.createElement('p');
severity.textContent = 'Severity: ' + report.severity;

// Add the information to the popup
popup.appendChild(reportTitle);
popup.appendChild(severity);

const detailLink = document.createElement('a');
detailLink.href = '/reports/' + report.id;
detailLink.textContent = 'View Report Details';
popup.appendChild(detailLink);

// Attach the popup to the red circle
potholeMarker.bindPopup(popup);

            // Add the circle to the potholes layer
            potholeMarker.addTo(potholesLayer);

        });

      }
async function loadPotholes(region) {
    console.log('Loading potholes for region:', region);
    potholesLayer.clearLayers();
try {
const url = new URL('/api/reports', window.location.origin);
url.searchParams.set('region', region);
const response = await fetch(url);
const data = await response.json();
if (!response.ok) {
console.error('Failed to load pothole reports:', data);
 alert("We couldn't load the pothole reports for the selected region. Please try again later.");
return;
 }
displayPotholes(data.reports);
} catch (error) {
console.error('Unable to load pothole reports:', error);
alert("We couldn't retrieve the pothole reports. Please check your internet connection and try again.");
}
}


    // Get the road search form
    const searchForm = document.getElementById('road-search-form');
    const searchRoadsButton = document.getElementById('search-roads-button');

    // Get the paragraph used to display search status messages
    const roadStatus = document.getElementById('road-status');

    
const useMyLocationButton = document.getElementById('use-my-location');

useMyLocationButton.addEventListener('click', function() {

    // Check if geolocation is supported
    if (!navigator.geolocation) {
        alert('Geolocation is not supported by your browser.');
        return;
    }

    // Request the user's current location
    navigator.geolocation.getCurrentPosition(

        // Runs if the location is retrieved successfully
        function(position) {

            const latitude = position.coords.latitude;
            const longitude = position.coords.longitude;

            console.log('Current latitude:', latitude);
            console.log('Current longitude:', longitude);

            // Update the selected location and blue marker
updateSelectedLocation(latitude, longitude);

// Center the map on the detected location
map.setView([latitude, longitude], 16);

        },

        // Runs if the location request fails
        function(error) {
            console.error('Unable to retrieve location:', error.message);
            alert("We couldn't retrieve your location. Please check your location permissions and try again, or select a location manually on the map.");
        }

    );

});


    // Get the pothole reporting form
const potholeReportForm = document.getElementById('pothole-report-form');
const submitPotholeButton = document.getElementById('submit-pothole-button');


potholeReportForm.addEventListener('submit', async function(event) {

  console.log('Pothole submit event detected');

    // Stop the browser from submitting the form
    event.preventDefault();

    if (submitPotholeButton.disabled) return;

    // Get the selected pothole coordinates
    const latitude = document.getElementById('pothole-latitude').value;
    const longitude = document.getElementById('pothole-longitude').value;

    // Check whether the user selected a location
    if (latitude === '' || longitude === '') {

        alert('Please select the pothole location on the map before submitting.');
        return;

    }

    // Confirm that all required information is available
    console.log('Pothole report form validated successfully');
    console.log('Latitude:', latitude);
    console.log('Longitude:', longitude);


// Collect the pothole report information from the form
const reportData = new FormData(potholeReportForm);
const description = reportData.get('description').trim();
if (description === '') {
    alert('Please provide a description of the pothole before submitting.');
    return;
}
reportData.set('description', description);
// Get the selected region
const region = document.getElementById('region').value;

// Check if a region was selected
if (region === '') {
    alert('Please select a region before submitting.');
    return;
}

// Add the region to the pothole report data
reportData.set('region', region);

// Display the selected region in the console
console.log('Selected region:', region);

    // Display the collected information in the console for testing
    console.log('Description:', reportData.get('description'));
    console.log('Severity:', reportData.get('severity'));
    console.log('Latitude:', reportData.get('latitude'));
    console.log('Longitude:', reportData.get('longitude'));

    // Get the selected photo
    const photo = reportData.get('photo');

    // Check whether a photo was selected
    if (photo && photo.size > 0) {
        console.log('Photo:', photo.name);
    } else {
        console.log('No photo selected');
    }

    submitPotholeButton.disabled = true;
    submitPotholeButton.textContent = 'Submitting...';

    try {
    const response = await fetch('/reports/new', {
        method: 'POST',
        body: reportData});

    if (!response.ok) {
    console.error('Failed to submit pothole report');
    alert("We couldn't submit your pothole report. Please check the selected location and report details, then try again.");
    return;}

    if (response.redirected && response.url.includes('/reports/')) {
    window.location.href = response.url;
    return;}

    if (response.redirected && response.url.includes('/login')) {
    window.location.href = response.url;
        return;}

console.error('Unexpected response after submitting pothole report');
alert("We couldn't confirm whether your pothole report was submitted successfully. Please check your reports before trying again to avoid submitting a duplicate.");
} catch (error) {
console.error('Unable to submit pothole report:', error);
alert("We couldn't connect to the server. Please check your internet connection and try submitting your report again.");
}
finally {
    submitPotholeButton.disabled = false;
    submitPotholeButton.textContent = 'Submit Pothole Report';
}


});



    // Detect when the user submits the form
    searchForm.addEventListener('submit', async function(event) {

        // Prevent the browser from reloading the page
        event.preventDefault();
        if (searchRoadsButton.disabled) return;

        // Check that the form submission was detected
        console.log('Search form submitted');

        // Get the selected region
        const region = document.getElementById('region').value;
        if (region === '') {
    alert('Please select a region.');
    return;
}

roadsLayer.clearLayers();
roadStatus.textContent = 'Loading roads...';
searchRoadsButton.disabled = true;
searchRoadsButton.textContent = 'Searching...';
try {

await loadPotholes(region);

        // Get the road name entered by the user
        const roadName = document.getElementById('road-name').value;

        // Get the selected road surface
        const surface = document.getElementById('surface').value;

        // Check whether service roads should be included
        const includeService = document.getElementById('include-service').checked;


        // Display the values in the console for testing
        console.log('Region:', region);
        console.log('Road name:', roadName);
        console.log('Surface:', surface);
        console.log('Include service roads:', includeService);


        // Create the URL for the roads API
        const url = new URL('/roads', window.location.origin);

        // Add the selected region (required)
        url.searchParams.set('region', region);

        // Add the road name if provided
        if (roadName.trim() !== '') {
            url.searchParams.set('name', roadName.trim());
        }

        // Add the surface filter if selected
        if (surface !== '') {
            url.searchParams.set('surface', surface);
        }

        // Include service roads only when checked
        if (includeService) {
            url.searchParams.set('include_service', '1');
        }

        // Display the completed URL for testing
        console.log('API URL:', url.toString());

        // Send a GET request to the roads API
      
            const response = await fetch(url);

            // Convert the JSON response into a JavaScript object
            const data = await response.json();


            // Display an error message if the API request fails
            if (!response.ok) {

                // Handle invalid search parameters
                if (response.status === 400) {
                    roadStatus.textContent =
                        'Invalid search filters. Please check your selections.';
                }

                // Handle Overpass API failures or other server errors
                else {
                    roadStatus.textContent =
                        data.error || 'Unable to load roads. Please try again.';
                }

                // Display the error details in the console
                console.error('API error:', data);
                return;
            }


            // Display the retrieved road data in the console
            console.log('Road data:', data);


            // Display the number of roads found
            if (data.count === 0) {
                roadStatus.textContent =
                    'No roads found. Try changing your search filters.';
            } else {
                roadStatus.textContent = data.count + ' roads found.';
            }


            // Draw each road returned by the API
            data.roads.forEach(function(road) {

                // Create a line using the road coordinates
                const roadLine = L.polyline(road.coordinates, {
                    color: 'blue',
                    weight: 3
                });


                // Create a link to the road's details page
                const detailUrl = '/road/' + road.osm_type + '/' + road.osm_id;

                // Create the popup elements
                const popup = document.createElement('div');

                // Display the road name safely
                const title = document.createElement('strong');
                title.textContent = road.name || road.name_ar || 'Unnamed road';
                title.dir = 'auto';

                // Display the road classification
                const roadType = document.createElement('p');
                roadType.textContent = 'Road type: ' + (road.highway || 'Unknown');

                // Create the road details link
                const detailLink = document.createElement('a');
                detailLink.href = detailUrl;
                detailLink.textContent = 'View Road Details';

                // Add everything to the popup
                popup.appendChild(title);
                popup.appendChild(roadType);
                popup.appendChild(detailLink);

                // Attach the popup to the road line
                roadLine.bindPopup(popup);

                // Add the road line to the roads layer
                roadLine.addTo(roadsLayer);

            }); // End of the forEach loop


            // Automatically zoom to all roads after drawing them
            if (roadsLayer.getLayers().length > 0) {
                map.fitBounds(roadsLayer.getBounds());
            }


        } catch (error) {

            // Display a message if the network request fails
            roadStatus.textContent =
                'Unable to connect to the road data service. Please try again.';

            console.error('Failed to fetch roads:', error);
        }  finally {

    searchRoadsButton.disabled = false;
    searchRoadsButton.textContent = 'Search Roads';

}

    }); // End of the submit event listener
