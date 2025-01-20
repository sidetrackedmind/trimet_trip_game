// Description: This file contains the function to get nearby routes from the Trimet API.

function getNearbyRoutes(fromPlace) {
    // fromPlace is a string with the format "lat,lon"
    const baseUrl = "https://developer.trimet.org/ws/v1/stops";
  
    const params = new URLSearchParams({
        json: true,
        appId: "8CBD14D520C6026CC7EEE56A9",
      showRoutes: true,
      meters: 1200,
      ll: fromPlace
    });
  
    return new Promise((resolve, reject) => {
        fetch(`${baseUrl}?${params}`)
          .then(response => response.json())
          .then(data => {
            const routeNumbers = new Set();
            data.resultSet.location.forEach(loc => {
              loc.route.forEach(route => {
                routeNumbers.add(route.route);
              });
            });
            resolve(routeNumbers); // Resolve the promise with routeNumbers
          })
          .catch(error => {
            reject(error); // Reject the promise with error
          });
      });
    }