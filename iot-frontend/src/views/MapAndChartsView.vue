<!-- <template>
  <div class="map-and-charts-container">
    <h1>Sensor Map</h1>
    <div class="map-wrapper">
      <div class="map-container" ref="mapContainer"></div>
    </div>

    <transition name="slide-fade">
      <div v-if="showSidePanel" class="side-panel">
        <h2>{{ selectedLocationFromMap }}</h2>
        <h3>Indoor Sensors</h3>
        <ul>
          <li v-for="(sensor, index) in indoorSensors" :key="index">
            <label>
              <input type="radio" v-model="tempSelectedIndoor" :value="sensor" /> {{ sensor }}
            </label>
          </li>
        </ul>

        <h3>Outdoor Sensors</h3>
        <ul>
          <li v-for="(sensor, index) in outdoorSensors" :key="index">
            <label>
              <input type="radio" v-model="tempSelectedOutdoor" :value="sensor" /> {{ sensor }}
            </label>
          </li>
        </ul>

        <div class="button-group">
          <button class="primary-button" @click="applySensorSelection">Show</button>
          <button class="secondary-button" @click="closeSidePanel">Cancel</button>
        </div>
      </div>
    </transition>
    <SelectCharts ref="selectChartsComponent" />
  </div>
</template> -->

<!-- start 02/01/2025 feature/adjust_map_and_chart_layout -->
<template>
  <div class="map-and-charts-container">
    <h1>Sensor Map</h1>
    <div class="content-wrapper">
      <!-- Map Section -->
      <div class="map-wrapper">
        <div class="map-container" ref="mapContainer"></div>
      </div>

      <!-- Chart Section -->
      <div class="charts-wrapper">
        <SelectCharts ref="selectChartsComponent" />
      </div>
    </div>

    <transition name="slide-fade">
      <div v-if="showSidePanel" class="side-panel">
        <h2>{{ selectedLocationFromMap }}</h2>
        <h3>Indoor Sensors</h3>
        <ul>
          <li v-for="(sensor, index) in indoorSensors" :key="index">
            <label>
              <input type="radio" v-model="tempSelectedIndoor" :value="sensor" /> {{ sensor }}
            </label>
          </li>
        </ul>

        <h3>Outdoor Sensors</h3>
        <ul>
          <li v-for="(sensor, index) in outdoorSensors" :key="index">
            <label>
              <input type="radio" v-model="tempSelectedOutdoor" :value="sensor" /> {{ sensor }}
            </label>
          </li>
        </ul>

        <div class="button-group">
          <button class="primary-button" @click="applySensorSelection">Show</button>
          <button class="secondary-button" @click="closeSidePanel">Cancel</button>
        </div>
      </div>
    </transition>
  </div>
</template>
<!-- end 02/01/2025 feature/adjust_map_and_chart_layout -->

<script>
// Script section remains unchanged
import { ref, onMounted } from 'vue';
import L from 'leaflet';
import axios from 'axios';
import 'leaflet/dist/leaflet.css';
import SelectCharts from '../components/SelectCharts.vue';
import 'leaflet.markercluster'; // added on 02/11/2025 feature/add_marker_clustering
import 'leaflet.markercluster/dist/MarkerCluster.css';
import 'leaflet.markercluster/dist/MarkerCluster.Default.css';


export default {
  components: {
    SelectCharts
  },
  setup() {
    const mapContainer = ref(null);
    const locationData = ref({});
    const showSidePanel = ref(false);

    const selectedLocationFromMap = ref(null);
    const indoorSensors = ref([]);
    const outdoorSensors = ref([]);
    const tempSelectedIndoor = ref('None');
    const tempSelectedOutdoor = ref('None');

    const selectChartsComponent = ref(null);

    const loadLocations = async () => {
      const response = await axios.get('/locations.json');
      locationData.value = response.data;
    };

    // const initMap = () => {
    //   // const map = L.map(mapContainer.value).setView([33.78, -84.4], 10); // feature/add_zoom_adjustment
    //   const map = L.map(mapContainer.value);
    //   const bounds = [];

    //   for (const locName in locationData.value) {
    //     const { latitude, longitude } = locationData.value[locName].coordinates;
    //     bounds.push([latitude, longitude]);
    //   }

    //   if (bounds.length > 0) {
    //     map.fitBounds(bounds); // Adjusts the view to contain all markers
    //   } else {
    //     map.setView([33.78, -84.4], 12); // Fallback default view
    //   }
    //   //end modif - feature/add_zoom_adjustment
    //   L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    //     attribution: 'Map data © OpenStreetMap contributors'
    //   }).addTo(map);

    //   // Define a custom icon 20250201_add_location_icon
    //   const customIcon = L.icon({
    //     iconUrl: require('@/assets/location_1024px.png'), // Path to your marker icon
    //     iconSize: [24, 24], // Size of the icon
    //     iconAnchor: [12, 12], // Anchor point of the icon
    //     popupAnchor: [0, -12] // Popup position relative to the icon
    //   });

    //   for (const locName in locationData.value) {
    //     const { latitude, longitude } = locationData.value[locName].coordinates;

    //     // Add a marker with the custom icon 2025
    //     const marker = L.marker([latitude, longitude], { icon: customIcon }).addTo(map);
    //     marker.on('mouseover', () => {
    //       marker.setOpacity(0.7); // Highlight effect
    //     });

    //     marker.on('mouseout', () => {
    //       marker.setOpacity(1); // Reset opacity
    //     });

    //     marker.on('click', () => {
    //       selectedLocationFromMap.value = locName;
    //       indoorSensors.value = locationData.value[locName].indoor;
    //       outdoorSensors.value = locationData.value[locName].outdoor;
    //       tempSelectedIndoor.value = indoorSensors.value[0] || 'None';
    //       tempSelectedOutdoor.value = outdoorSensors.value[0] || 'None';
    //       showSidePanel.value = true;
    //     });
    //   }
    // };

    const initMap = () => {
      const map = L.map(mapContainer.value).setView([33.78, -84.4], 12);

      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: 'Map data © OpenStreetMap contributors'
      }).addTo(map);

      // Define the custom icon **before** using it
      const customIcon = L.icon({
        iconUrl: require('@/assets/location_1024px.png'), // Ensure this file exists
        iconSize: [24, 24],
        iconAnchor: [12, 12],
        popupAnchor: [0, -12]
      });

      const bounds = [];
      const markerClusterGroup = L.markerClusterGroup();

      for (const locName in locationData.value) {
        const { latitude, longitude } = locationData.value[locName].coordinates;
        bounds.push([latitude, longitude]);

        const marker = L.marker([latitude, longitude], { icon: customIcon });

        marker.on('mouseover', () => marker.setOpacity(0.7));
        marker.on('mouseout', () => marker.setOpacity(1));
        marker.on('click', () => {
          selectedLocationFromMap.value = locName;
          indoorSensors.value = locationData.value[locName].indoor;
          outdoorSensors.value = locationData.value[locName].outdoor;
          tempSelectedIndoor.value = indoorSensors.value[0] || 'None';
          tempSelectedOutdoor.value = outdoorSensors.value[0] || 'None';
          showSidePanel.value = true;
        });

        markerClusterGroup.addLayer(marker);
      }

      map.addLayer(markerClusterGroup);

      if (bounds.length > 0) {
        map.fitBounds(bounds);
      } else {
        map.setView([33.78, -84.4], 12);
      }
    };


    const applySensorSelection = () => {
      showSidePanel.value = false;

      if (selectChartsComponent.value) {
        selectChartsComponent.value.updateSensorsFromParent(
          selectedLocationFromMap.value,
          tempSelectedIndoor.value,
          tempSelectedOutdoor.value
        );
      }
    };

    const closeSidePanel = () => {
      showSidePanel.value = false;
    };

    onMounted(async () => {
      await loadLocations();
      initMap();
    });

    return {
      mapContainer,
      showSidePanel,
      selectedLocationFromMap,
      indoorSensors,
      outdoorSensors,
      tempSelectedIndoor,
      tempSelectedOutdoor,
      applySensorSelection,
      closeSidePanel,
      selectChartsComponent
    };
  }
};
</script>

<style scoped>
.map-and-charts-container {
  position: relative;
  width: 98%;
  height: 100%;
  padding: 20px;
}

/* start 02/01/2025 feature/adjust_map_and_chart_layout */
.content-wrapper {
  display: flex;
  /* Use flexbox to arrange map and chart side by side */
  gap: 16px;
  /* Add space between the map and chart */
}

/* end 02/01/2025 feature/adjust_map_and_chart_layout */

.map-wrapper {
  flex: 1;
  /* 02/01/2025 feature/adjust_map_and_chart_layout: Allow the map to take up one part of the available space */
  border-radius: 2px;
  overflow: hidden;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  border: 1px solid #e2e8f0;
  background-color: white;
  padding: 16px;
  /* margin-bottom: 24px; (commented on 02/01/2025 feature/adjust_map_and_chart_layout)*/
}

.map-container {
  width: 100%;
  height: 300px;
  border-radius: 0px;
  border: 1px solid black;
  overflow: hidden;
}

/* start 02/01/2025 feature/adjust_map_and_chart_layout */
.charts-wrapper {
  flex: 1;
  /* Allow the chart to take up one part of the available space */
  border-radius: 2px;
  overflow: hidden;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  border: 1px solid #e2e8f0;
  background-color: white;
  padding: 16px;
}

/* end 02/01/2025 feature/adjust_map_and_chart_layout */

.side-panel {
  position: absolute;
  top: 120px;
  right: 20px;
  width: 300px;
  background: white;
  border-radius: 2px;
  border: 1px solid #484e56;
  padding: 24px;
  z-index: 1000;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.side-panel h2 {
  margin-top: 0;
  margin-bottom: 16px;
  color: #2d3748;
  font-size: 1.25rem;
}

.side-panel h3 {
  color: #4a5568;
  margin-top: 16px;
  margin-bottom: 8px;
}

.side-panel ul {
  list-style: none;
  padding: 0;
  margin: 0 0 16px 0;
}

.side-panel li {
  margin-bottom: 8px;
}

.button-group {
  display: flex;
  gap: 12px;
  margin-top: 20px;
}

.primary-button,
.secondary-button {
  padding: 8px 16px;
  border-radius: 6px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.primary-button {
  background-color: #4299e1;
  color: white;
  border: none;
}

.primary-button:hover {
  background-color: #3182ce;
}

.secondary-button {
  background-color: white;
  color: #4a5568;
  border: 1px solid #e2e8f0;
}

.secondary-button:hover {
  background-color: #f7fafc;
}

.slide-fade-enter-active,
.slide-fade-leave-active {
  transition: all 0.3s ease;
}

.slide-fade-enter-from,
.slide-fade-leave-to {
  opacity: 0;
  transform: translateX(20px);
}
</style>