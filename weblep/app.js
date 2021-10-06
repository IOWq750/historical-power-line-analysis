const yearRange = document.getElementById("yearrange")
const yearLabel = document.getElementById("yearlabel")
yearLabel.innerText = yearRange.value
const isoYear = yearRange.value + "-01-01"

const map = L.map('mapid').setView([56.5, 37.09], 7);
const osm = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors' });
const satellite = L.tileLayer("https://api.mapbox.com/styles/v1/mapbox/satellite-v9/tiles/{z}/{x}/{y}?access_token=pk.eyJ1IjoiaW93cTc1MCIsImEiOiJja3QwYzJpazMwN2ltMnVwOW0zbnJrOWh4In0.bBbrEq6D4MkMvX--IxJVUw")

// OSM.addTo(map)
satellite.addTo(map)
const getWMSLayer = function (layerId, time) {
    return (
        L.tileLayer.wms('https://powerlines.one/wms?', {
            layers: layerId,
            transparent: true,
            format: 'image/png',
            time: time
        })
    )
}
const pl_voltage = getWMSLayer("pl_voltage", isoYear).addTo(map)
const pl_modifications = getWMSLayer("pl_modifications", isoYear)
const endpoints = getWMSLayer("endpoints", isoYear).addTo(map)


const basemapControls = {
    "Satellite": satellite,
    "OSM": osm
}

const layersControls = {
    "Voltage of power lines": pl_voltage,
    "Modifications of power lines": pl_modifications,
    "Plants & substations": endpoints
}

L.control.layers(basemapControls, layersControls).addTo(map);


const updateYearLabel = function () {
    yearLabel.innerText = this.value
}

const updateYearValue = function () {
    const yearValue = this.value
    this.setAttribute("value", yearValue)
    const yearIso = yearValue + "-01-01"
    pl_voltage.setParams({time: yearIso})
    pl_modifications.setParams({time: yearIso})
    endpoints.setParams({time: yearIso})
    // other.setParams({time: yearIso})
}


yearRange.oninput = updateYearLabel
yearRange.onchange = updateYearValue






