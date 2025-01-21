// Description: This script is used to get the trip plan from Trimet API.

function getTrimetPlan(fromPlace, toPlace, maxWalkDistance = 805, walkSpeed = 1.34, numItineraries = 1) {
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

    return new Promise((resolve, reject) => {
      fetch(`${baseUrl}?${params}`)
    .then(response => response.json())
    .then(data => {
      // only deal with 1 itinerary for now
      const itinerary = data.plan.itineraries[0];
      const legs = itinerary.legs;
      const trimetLegs = legs.filter(leg => 
        leg.mode === 'BUS' || leg.mode === 'TRAM' || leg.mode === 'RAIL' || leg.mode === 'GONDOLA'
      );
          resolve(trimetLegs); // Resolve the promise with routeNumbers
        })
        .catch(error => {
          reject(error); // Reject the promise with error
        });
    });
  }