/* eslint-disable @typescript-eslint/no-explicit-any */
declare module "leaflet" {
  const L: any;
  export default L;
  export = L;
}

declare module "leaflet.markercluster" {
  const mc: any;
  export default mc;
}

declare module "leaflet/dist/leaflet.css" {
  const content: any;
  export default content;
}

declare module "leaflet.markercluster/dist/MarkerCluster.css" {
  const content: any;
  export default content;
}

declare module "leaflet.markercluster/dist/MarkerCluster.Default.css" {
  const content: any;
  export default content;
}

declare module "leaflet/dist/images/marker-icon-2x.png" {
  const value: string;
  export default value;
}

declare module "leaflet/dist/images/marker-icon.png" {
  const value: string;
  export default value;
}

declare module "leaflet/dist/images/marker-shadow.png" {
  const value: string;
  export default value;
}
