// Description: This script is used to get the trip plan from Trimet API.

function getTrimetPlan(fromPlace, toPlace, maxWalkDistance = 1200, walkSpeed = 1.7, numItineraries = 1) {
    const baseUrl = "https://maps.trimet.org/otp_mod/plan";
  
    // 805 meters = 1/2 mile. 1.7 m/s 
  
    const now = new Date();
  
    const year = now.getFullYear();
    const month = String(now.getMonth() + 1).padStart(2, '0'); // Months are 0-indexed
    const day = String(now.getDate()).padStart(2, '0');
  
    const hours = String(now.getHours()).padStart(2, '0');
    const minutes = String(now.getMinutes()).padStart(2, '0');
  
    const date = `${year}-${month}-${day}`; 
    const time = `${hours}:${minutes}`;
  
    const params = new URLSearchParams({
      fromPlace,
      toPlace,
      date,
      time,
      mode: "WALK,BUS,TRAM,RAIL,GONDOLA",
      maxWalkDistance,
      walkSpeed,
      numItineraries,
    });

    var xhReq = new XMLHttpRequest();
    xhReq.open("GET", `${baseUrl}?${params}`, false);
    xhReq.send(null);
    var raw_response = JSON.parse(xhReq.responseText);
    return raw_response;

    }