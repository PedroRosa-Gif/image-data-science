#include "ift.h"

float getTrilinearValue(iftImage *img, float x, float y, float z) {
  int x0 = (int)floor(x);
  int y0 = (int)floor(y);
  int z0 = (int)floor(z);
  int x1 = x0 + 1;
  int y1 = y0 + 1;
  int z1 = z0 + 1;

  if (x0 < 0 || x1 >= img->xsize || y0 < 0 || y1 >= img->ysize || z0 < 0 || z1 >= img->zsize) {
    iftVoxel v = {(int)round(x), (int)round(y), (int)round(z)};
    if (iftValidVoxel(img, v)) return img->val[iftGetVoxelIndex(img, v)];
    return 0;
  }

  float dx = x - x0;
  float dy = y - y0;
  float dz = z - z0;

  float v1 = img->val[iftGetVoxelIndex(img, ((iftVoxel){x0, y0, z0}))];
  float v2 = img->val[iftGetVoxelIndex(img, ((iftVoxel){x1, y0, z0}))];
  float v3 = img->val[iftGetVoxelIndex(img, ((iftVoxel){x0, y1, z0}))];
  float v4 = img->val[iftGetVoxelIndex(img, ((iftVoxel){x1, y1, z0}))];
  float v5 = img->val[iftGetVoxelIndex(img, ((iftVoxel){x0, y0, z1}))];
  float v6 = img->val[iftGetVoxelIndex(img, ((iftVoxel){x1, y0, z1}))];
  float v7 = img->val[iftGetVoxelIndex(img, ((iftVoxel){x0, y1, z1}))];
  float v8 = img->val[iftGetVoxelIndex(img, ((iftVoxel){x1, y1, z1}))];

  float i13 = v1 * (1.0f - dy) + v3 * dy;
  float i24 = v2 * (1.0f - dy) + v4 * dy;
  float i57 = v5 * (1.0f - dy) + v7 * dy;
  float i68 = v6 * (1.0f - dy) + v8 * dy;

  float i1324 = i13 * (1.0f - dx) + i24 * dx;
  float i5768 = i57 * (1.0f - dx) + i68 * dx;

  return i1324 * (1.0f - dz) + i5768 * dz;
}

iftImage *getSlice(iftImage *img, iftPoint p0, int diag, float alpha, float beta) {
  iftImage *slice = iftCreateImage(diag, diag, 1);
  iftPoint center_slice = {slice->xsize/2.0f, slice->ysize/2.0f, 0.0f};

  iftMatrix *Rx = iftRotationMatrix(IFT_AXIS_X, alpha);
  iftMatrix *Ry = iftRotationMatrix(IFT_AXIS_Y, beta);
  iftMatrix *R  = iftMultMatrices(Ry, Rx);

  for (int v = 0; v < slice->ysize; v++) {
    for (int u = 0; u < slice->xsize; u++) {
      float p_x = u - center_slice.x;
      float p_y = v - center_slice.y;

      iftPoint pl;
      pl.x = (R->val[0]*p_x + R->val[1]*p_y) + p0.x;
      pl.y = (R->val[4]*p_x + R->val[5]*p_y) + p0.y;
      pl.z = (R->val[8]*p_x + R->val[9]*p_y) + p0.z;

      iftImgVal(slice, u, v, 0) = (int)round(getTrilinearValue(img, pl.x, pl.y, pl.z));
    }
  }

  iftDestroyMatrix(&Rx); iftDestroyMatrix(&Ry); iftDestroyMatrix(&R);
  return slice;
}

iftImage *reslicing(iftImage *img, iftPoint p0, int n_slices, float lambda, iftVector n, int diag, float alpha, float beta) {
  iftImage *new_scene = iftCreateImage(diag, diag, n_slices);
  new_scene->dz = lambda * img->dz;
  int slice_size = diag * diag;

  for (int k = 0; k < n_slices; k++) {
    iftPoint pk;
    pk.x = p0.x + (k * lambda * n.x);
    pk.y = p0.y + (k * lambda * n.y);
    pk.z = p0.z + (k * lambda * n.z);

    iftImage *slice = getSlice(img, pk, diag, alpha, beta);
    
    for (int i = 0; i < slice_size; i++) {
      new_scene->val[k * slice_size + i] = slice->val[i];
    }

    iftDestroyImage(&slice);
  }

  return new_scene;
}

int main(int argc, char *argv[]) {
  if (argc != 10) {
    iftError("Uso: ./reslicing P1 x0 y0 z0 xn-1 yn-1 zn-1 n P5", "main");
  }

  char *input_path = argv[1];
  iftImage *img = iftReadImageByExt(input_path);

  iftPoint p0, pn_1;
  
  p0.x = atof(argv[2]);
  p0.y = atof(argv[3]);
  p0.z = atof(argv[4]);
  pn_1.x = atof(argv[5]);
  pn_1.y = atof(argv[6]);
  pn_1.z = atof(argv[7]);

  int n_slices = atoi(argv[8]);
  char *output_path = argv[9];

  iftVector dir = {pn_1.x - p0.x, pn_1.y - p0.y, pn_1.z - p0.z};
  float dist = sqrt(dir.x*dir.x + dir.y*dir.y + dir.z*dir.z);
  iftVector n = {dir.x/dist, dir.y/dist, dir.z/dist};

  float beta  = atan2f(n.x, n.z) * 180.0f / PI;
  float alpha = asinf(-n.y) * 180.0f / PI;
  float lambda = (n_slices > 0) ? dist / (float)n_slices : 0;

  int diag = (int)ceil(sqrt(img->xsize*img->xsize + img->ysize*img->ysize + img->zsize*img->zsize));
  iftImage *new_scene = reslicing(img, p0, n_slices, lambda, n, diag, alpha, beta);

  iftImage *normalized = iftNormalize(new_scene, 0, 255);

  iftWriteImageByExt(normalized, output_path);

  iftDestroyImage(&img);
  iftDestroyImage(&normalized);
  iftDestroyImage(&new_scene);

  return 0;
}