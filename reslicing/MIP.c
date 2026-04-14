#include "ift.h"

int BITS = 16;

void drawWireframe(iftImage *canvas, iftImage *img, iftMatrix *R, int H) {
    iftPoint center_can = {canvas->xsize / 2.0f, canvas->ysize / 2.0f, 0.0f};
    iftAdjRel *A = iftCircular(1.5f);

    float dx = img->xsize / 2.0f;
    float dy = img->ysize / 2.0f;
    float dz = img->zsize / 2.0f;

    iftPoint v[8] = {
        {-dx, -dy, -dz}, {dx, -dy, -dz}, {dx, dy, -dz}, {-dx, dy, -dz},
        {-dx, -dy,  dz}, {dx, -dy,  dz}, {dx, dy,  dz}, {-dx, dy,  dz}
    };

    int faces[6][4] = {
        {0, 1, 2, 3}, {4, 5, 6, 7}, {0, 4, 7, 3},
        {1, 5, 6, 2}, {0, 1, 5, 4}, {3, 2, 6, 7}
    };
    iftVector normals[6] = {
        {0,0,-1}, {0,0,1}, {-1,0,0}, {1,0,0}, {0,-1,0}, {0,1,0}
    };

    iftColor color; 
    color.val[0] = H; 

    for (int i = 0; i < 6; i++) {
        iftVector rn = iftTransformVector(R, normals[i]);

        if (rn.z < 0) {
            for (int j = 0; j < 4; j++) {
                iftPoint p1_rot = iftTransformPoint(R, v[faces[i][j]]);
                iftPoint p2_rot = iftTransformPoint(R, v[faces[i][(j + 1) % 4]]);

                iftVoxel v1 = {(int)round(p1_rot.x + center_can.x), 
                               (int)round(p1_rot.y + center_can.y), 0};
                iftVoxel v2 = {(int)round(p2_rot.x + center_can.x), 
                               (int)round(p2_rot.y + center_can.y), 0};

                if (iftValidVoxel(canvas, v1) && iftValidVoxel(canvas, v2)) {
                    iftDrawLine(canvas, v1, v2, color, A);
                }
            }
        }
    }
}

iftImage *applyColorMap(iftImage *img) {
  int H = (int)pow(2, BITS) - 1;

  iftImage *color_img = iftCreateColorImage(img->xsize, img->ysize, img->zsize, H);

  int i_max = iftMaximumValue(img);
  if (i_max <= 0) i_max = 1;

  for (int i = 0; i < img->n; i++) {
    float V = (float)img->val[i] / i_max;
    V = 4.0f * V + 1.0f;

    float Rf = H * fmaxf(0.0f, (3.0f - fabsf(V - 4.0f) - fabsf(V - 5.0f)) / 2.0f);
    float Gf = H * fmaxf(0.0f, (4.0f - fabsf(V - 2.0f) - fabsf(V - 4.0f)) / 2.0f);
    float Bf = H * fmaxf(0.0f, (3.0f - fabsf(V - 1.0f) - fabsf(V - 2.0f)) / 2.0f);

    iftColor rgb;
    rgb.val[0] = Rf;
    rgb.val[1] = Gf;
    rgb.val[2] = Bf;

    iftColor ycbcr = iftRGBtoYCbCr(rgb, H);

    color_img->val[i] = ycbcr.val[0];
    color_img->Cb[i]  = ycbcr.val[1];
    color_img->Cr[i]  = ycbcr.val[2];
  }

  return color_img;
}

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

float DDA(iftImage *img, iftPoint start, float dx, float dy, float dz, int steps) {
  float max_val = 0;
  float vx = start.x;
  float vy = start.y;
  float vz = start.z;

  for (int k = 0; k < steps; k++) {
      float intensity = getTrilinearValue(img, vx, vy, vz);
      
      if (intensity > max_val) {
          max_val = intensity;
      }

      vx += dx;
      vy += dy;
      vz += dz;
  }
  return max_val;
}

int main(int argc, char *argv[]) {
  if (argc < 5 || argc > 6) {
    iftError("Uso: ./MIP P1 P2 P3 [P4] P5", "main");
  }

  iftImage *img = iftReadImageByExt(argv[1]);
  float alpha = atof(argv[2]);
  float beta = atof(argv[3]);
  iftImage *mask = (argc == 6) ? iftReadImageByExt(argv[4]) : NULL;
  char *out_path = (argc == 6) ? argv[5] : argv[4];
  char path_png[256];
  char path_colored[256];

  if (mask != NULL) {
    for (int p = 0; p < img->n; p++) {
      if (mask->val[p] == 0) img->val[p] = 0;
    }
  }

  iftMatrix *Rx = iftRotationMatrix(IFT_AXIS_X, alpha);
  iftMatrix *Ry = iftRotationMatrix(IFT_AXIS_Y, beta);
  iftMatrix *R  = iftMultMatrices(Ry, Rx);

  float dx = R->val[2];
  float dy = R->val[6];
  float dz = R->val[10];

  int diag = (int)ceil(sqrt(img->xsize*img->xsize + img->ysize*img->ysize + img->zsize*img->zsize));
  iftImage *canvas = iftCreateImage(diag, diag, 1);
  
  iftPoint center_vol = {img->xsize/2.0, img->ysize/2.0, img->zsize/2.0};
  iftPoint center_can = {canvas->xsize/2.0, canvas->ysize/2.0, 0};
  
  #pragma omp parallel for collapse(2)
  for (int v = 0; v < canvas->ysize; v++) {
    for (int u = 0; u < canvas->xsize; u++) {
      float p_x = u - center_can.x;
      float p_y = v - center_can.y;
      float dist_ini = -diag / 2.0;

      iftPoint p_start;
      p_start.x = (R->val[0]*p_x + R->val[1]*p_y + dx*dist_ini) + center_vol.x;
      p_start.y = (R->val[4]*p_x + R->val[5]*p_y + dy*dist_ini) + center_vol.y;
      p_start.z = (R->val[8]*p_x + R->val[9]*p_y + dz*dist_ini) + center_vol.z;

      float intensity = DDA(img, p_start, dx, dy, dz, diag);
      
      iftImgVal(canvas, u, v, 0) = (int)intensity;
    }
  }

  iftImage *final_img = iftNormalize(canvas, 0, 65535);

  drawWireframe(final_img, img, R, 65535);

  sprintf(path_png, "%s.png", out_path);
  sprintf(path_colored, "%s_colored.png", out_path);

  iftWriteImageByExt(final_img, path_png);

  iftImage *colored = applyColorMap(final_img);
  iftWriteImageByExt(colored, path_colored);

  iftDestroyImage(&colored);
  iftDestroyImage(&img); iftDestroyImage(&canvas); iftDestroyImage(&final_img);
  if (mask) iftDestroyImage(&mask);
  iftDestroyMatrix(&Rx); iftDestroyMatrix(&Ry); iftDestroyMatrix(&R);

  return 0;
}
