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
  const routeNumbers = new Set();
  var xhReq = new XMLHttpRequest();
  xhReq.open("GET", `${baseUrl}?${params}`, false);
  xhReq.send(null);
  var raw_response = JSON.parse(xhReq.responseText);
  raw_response.resultSet.location.forEach(loc => {
    loc.route.forEach(route => {
      routeNumbers.add(route.route);
      console.log(route.route);
    });
  });
  return routeNumbers;
  }