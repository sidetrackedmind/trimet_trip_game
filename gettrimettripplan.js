// Description: This script is used to get the trip plan from Trimet API.

function getTrimetPlan(fromPlace, toPlace, maxWalkDistance = 805, walkSpeed = 1.34, numItineraries = 3) {
    const baseUrl = "https://maps.trimet.org/otp_mod/plan";
  
    // 805 meters = 1/2 mile. 1.34 m/s = 3 mph
  
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
  
    fetch(`${baseUrl}?${params}`)
    .then(response => response.json())
    .then(data => {
      console.log("Trimet API response:", data);
    })
    .catch(error => {
      console.error("Error fetching Trimet directions:", error);
    });
  }