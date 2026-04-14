#include "ift.h"

typedef enum { AXIAL, CORONAL, SAGITAL } Plan;

int BITS = 16;

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

iftImage *applyLinearStretching(iftImage *img, double w, double l) {
  int k1 = 0;
  int k2 = (int)pow(2, BITS) - 1;
  int i_min = iftMinimumValue(img);
  int i_max = iftMaximumValue(img);
  double range = (double)i_max - i_min;

  double level  = (double)i_min + (l / 100.0) * range;
  double window = (w / 100.0) * range;

  if (window <= 0.0) window = 1.0;

  double l1 = level - (window / 2.0f);
  double l2 = level + (window / 2.0f);

  iftImage *out = iftCreateImage(img->xsize, img->ysize, img->zsize);
  int n_voxels = img->xsize * img->ysize * img->zsize;

  double slope = (double)(k2 - k1) / window;

  for (int i = 0; i < n_voxels; i++) {
    double I = (double)img->val[i];
    
    if (I < l1) {
      out->val[i] = k1;
    } else if (I >= l2) {
      out->val[i] = k2;
    } else {
      out->val[i] = (int)roundf(slope * (I - l1) + k1);
    }
  }

  return out;
}

void getBaseName(const char *path, char *output) {
  const char *base = strrchr(path, '/');
  if (base) base++;
  else base = path;

  strcpy(output, base);

  char *dot = strrchr(output, '.');
  if (dot) *dot = '\0';
}

iftImage *getSlice(iftImage *img, int origin, Plan plan) {
  iftImage *slice = NULL;

  switch (plan) {
    case AXIAL:
      slice = iftCreateImage(img->xsize, img->ysize, 1);
      for (int y = 0; y < img->ysize; y++) {
        for (int x = 0; x < img->xsize; x++) {
          int src_idx = iftGetVoxelIndex(img, ((iftVoxel){x, y, origin}));
          int dst_idx = iftGetVoxelIndex(slice, ((iftVoxel){x, y, 0}));
          slice->val[dst_idx] = img->val[src_idx];
        }
      }
      break;
    case CORONAL:
      slice = iftCreateImage(img->xsize, img->zsize, 1);
      for (int z = 0; z < img->zsize; z++) {
          for (int x = 0; x < img->xsize; x++) {
            int src_idx = iftGetVoxelIndex(img, ((iftVoxel){x, origin, z}));
            int dst_idx = iftGetVoxelIndex(slice, ((iftVoxel){x, z, 0}));
            slice->val[dst_idx] = img->val[src_idx];
          }
      }
      break;
    case SAGITAL:
      slice = iftCreateImage(img->ysize, img->zsize, 1);
      for (int z = 0; z < img->zsize; z++) {
        for (int y = 0; y < img->ysize; y++) {
          int src_idx = iftGetVoxelIndex(img, ((iftVoxel){origin, y, z}));
          int dst_idx = iftGetVoxelIndex(slice, ((iftVoxel){y, z, 0}));
          slice->val[dst_idx] = img->val[src_idx];
        }
      }
      break;
  }

  return slice;
}

int main(int argc, char *argv[]) {
  if (argc != 4) {
    iftError("Uso: %s <imagem.scn>", "main", argv[0]);
  }

  char path[512];
  char base_name[256];
  getBaseName(argv[1], base_name);

  iftImage *img = iftReadImage(argv[1]);

  iftImage *img_stretched = applyLinearStretching(img, atof(argv[2]), atof(argv[3]));

  iftImage *axial   = getSlice(img_stretched, img->zsize / 2, AXIAL);
  iftImage *coronal = getSlice(img_stretched, img->ysize / 2, CORONAL);
  iftImage *sagital = getSlice(img_stretched, img->xsize / 2, SAGITAL);

  iftImage *color_axial = applyColorMap(axial);
  iftImage *color_coronal = applyColorMap(coronal);
  iftImage *color_sagital = applyColorMap(sagital);

  sprintf(path, "results/plans/%s_axial.png", base_name);
  iftWriteImageByExt(axial, path);
  sprintf(path, "results/plans/%s_coronal.png", base_name);
  iftWriteImageByExt(coronal, path);
  sprintf(path, "results/plans/%s_sagital.png", base_name);
  iftWriteImageByExt(sagital, path);

  sprintf(path, "results/colors/%s_axial_color.png", base_name);
  iftWriteImageByExt(color_axial, path);
  sprintf(path, "results/colors/%s_coronal_color.png", base_name);
  iftWriteImageByExt(color_coronal, path);
  sprintf(path, "results/colors/%s_sagital_color.png", base_name);
  iftWriteImageByExt(color_sagital, path);

  iftDestroyImage(&img);
  iftDestroyImage(&axial);
  iftDestroyImage(&coronal);
  iftDestroyImage(&sagital);

  return 0;
}