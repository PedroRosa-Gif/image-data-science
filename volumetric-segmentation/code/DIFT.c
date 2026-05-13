#include "ift.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

typedef struct {
  iftFImage *cost;
  iftImage  *label;
  iftImage  *root;
  iftImage  *pred;
  iftSet   **tree_nodes;
} Forest;

float *compute_gradient(iftImage *img, iftAdjRel *A) {
  float *G = (float *) calloc(img->n, sizeof(float));

  for (int p = 0; p < img->n; p++) {
    iftVoxel u   = iftGetVoxelCoord(img, p);
    float    sum = 0.0f;
    int      cnt = 0;

    for (int i = 1; i < A->n; i++) {
      iftVoxel v = iftGetAdjacentVoxel(A, u, i);
      if (iftValidVoxel(img, v)) {
        int q = iftGetVoxelIndex(img, v);
        sum  += fabsf((float)(img->val[p] - img->val[q]));
        cnt++;
      }
    }
    if (cnt > 0) G[p] = sum / cnt;
  }
  return G;
}

void write_fimage_scn(iftFImage *fim, const char *path) {
  FILE *f = fopen(path, "wb");
  if (!f) {
    fprintf(stderr, "Erro ao abrir %s para escrita\n", path);
    return;
  }
  fprintf(f, "SCN\n");
  fprintf(f, "%d %d %d\n", fim->xsize, fim->ysize, fim->zsize);
  fprintf(f, "1.0 1.0 1.0\n");
  fprintf(f, "32\n");
  fwrite(fim->val, sizeof(float), fim->n, f);
  fclose(f);
}

iftFImage *read_fimage_scn(const char *path) {
  FILE *f = fopen(path, "rb");
  if (!f) {
    fprintf(stderr, "Erro ao abrir %s para leitura\n", path);
    return NULL;
  }

  char magic[16];
  int  x, y, z, bits;
  fscanf(f, "%s\n", magic);
  fscanf(f, "%d %d %d\n", &x, &y, &z);
  fscanf(f, "%*f %*f %*f\n");
  fscanf(f, "%d\n", &bits);

  iftFImage *fim = iftCreateFImage(x, y, z);
  fread(fim->val, sizeof(float), fim->n, f);
  fclose(f);
  return fim;
}

Forest *compute_mst(iftImage *img, iftAdjRel *A, float *G) {
  Forest *F = (Forest *) calloc(1, sizeof(Forest));

  F->cost       = iftCreateFImage(img->xsize, img->ysize, img->zsize);
  F->pred       = iftCreateImage (img->xsize, img->ysize, img->zsize);
  F->root       = iftCreateImage (img->xsize, img->ysize, img->zsize);
  F->label      = iftCreateImage (img->xsize, img->ysize, img->zsize);
  F->tree_nodes = (iftSet **) calloc(img->n, sizeof(iftSet *));

  iftFHeap *Q = iftCreateFHeap(img->n, F->cost->val);

  for (int p = 0; p < img->n; p++) {
    F->cost->val[p] = IFT_INFINITY_FLT;
    F->pred->val[p] = IFT_NIL;
    F->root->val[p] = p;
  }

  F->cost->val[0] = 0.0f;
  iftInsertFHeap(Q, 0);

  while (!iftEmptyFHeap(Q)) {
    int      p = iftRemoveFHeap(Q);
    iftVoxel u = iftGetVoxelCoord(img, p);

    for (int i = 1; i < A->n; i++) {
      iftVoxel v = iftGetAdjacentVoxel(A, u, i);
      if (!iftValidVoxel(img, v)) continue;

      int   q = iftGetVoxelIndex(img, v);
      float w = (G[p] + G[q]) / 2.0f;

      if (w < F->cost->val[q]) {
        F->cost->val[q] = w;
        F->pred->val[q] = p;

        if (Q->color[q] == IFT_WHITE)
          iftInsertFHeap(Q, q);
        else
          iftGoUpFHeap(Q, Q->pos[q]);
      }
    }
  }

  iftDestroyFHeap(&Q);
  return F;
}

iftLabeledSet *recover_seeds(Forest *F, iftImage *init_seg) {
  char          *inserted = (char *) calloc(init_seg->n, sizeof(char));
  iftLabeledSet *seeds    = NULL;
  int            count    = 0;

  for (int p = 0; p < init_seg->n; p++) {
    int pr = F->pred->val[p];
    if (pr == IFT_NIL) continue;

    if (init_seg->val[p] != init_seg->val[pr]) {
      if (!inserted[p]) {
        int label_bin = (init_seg->val[p] == 21844) ? 1 : 2;
        iftInsertLabeledSet(&seeds, p, label_bin);
        inserted[p] = 1;
        count++;
      }
      if (!inserted[pr]) {
        int label_bin = (init_seg->val[pr] == 21844) ? 1 : 2;
        iftInsertLabeledSet(&seeds, pr, label_bin);
        inserted[pr] = 1;
        count++;
      }
    }
  }

  free(inserted);
  printf("Sementes recuperadas: %d\n", count);
  return seeds;
}

void run_ift(Forest *F, iftImage *img, iftAdjRel *A, iftLabeledSet *seeds, iftSet *border_nodes, float *G, int full_reset) {
  if (full_reset) {
    for (int p = 0; p < img->n; p++) {
      F->cost->val[p]  = IFT_INFINITY_FLT;
      F->pred->val[p]  = IFT_NIL;
      F->root->val[p]  = p;
      F->label->val[p] = 0;
      if (F->tree_nodes[p]) {
        iftDestroySet(&F->tree_nodes[p]);
        F->tree_nodes[p] = NULL;
      }
    }
  }

  iftFHeap *Q = iftCreateFHeap(img->n, F->cost->val);

  iftLabeledSet *s = seeds;
  while (s != NULL) {
    int p = s->elem;
    F->cost->val[p]  = 0.0f;
    F->pred->val[p]  = IFT_NIL;
    F->root->val[p]  = p;
    F->label->val[p] = s->label;

    if (F->tree_nodes[p]) {
      iftDestroySet(&F->tree_nodes[p]);
      F->tree_nodes[p] = NULL;
    }
    iftInsertSet(&F->tree_nodes[p], p);
    iftInsertFHeap(Q, p);
    s = s->next;
  }

  iftSet *bn = border_nodes;
  while (bn != NULL) {
    int p = bn->elem;
    if (Q->color[p] == IFT_WHITE && F->cost->val[p] < IFT_INFINITY_FLT)
      iftInsertFHeap(Q, p);
    bn = bn->next;
  }

  while (!iftEmptyFHeap(Q)) {
    int      p = iftRemoveFHeap(Q);
    iftVoxel u = iftGetVoxelCoord(img, p);

    for (int i = 1; i < A->n; i++) {
      iftVoxel v = iftGetAdjacentVoxel(A, u, i);
      if (!iftValidVoxel(img, v)) continue;

      int   q   = iftGetVoxelIndex(img, v);
      float w   = (G[p] + G[q]) / 2.0f;
      float tmp = fmaxf(F->cost->val[p], w);

      if (tmp < F->cost->val[q] ||
          (tmp == F->cost->val[q] && F->pred->val[q] == p)) {

        if (F->cost->val[q] < IFT_INFINITY_FLT) {
          int old_root = F->root->val[q];
          iftRemoveSetElem(&F->tree_nodes[old_root], q);
        }

        F->cost->val[q]  = tmp;
        F->pred->val[q]  = p;
        F->root->val[q]  = F->root->val[p];
        F->label->val[q] = F->label->val[p];
        iftInsertSet(&F->tree_nodes[F->root->val[q]], q);

        if (Q->color[q] == IFT_WHITE)
          iftInsertFHeap(Q, q);
        else
          iftGoUpFHeap(Q, Q->pos[q]);
      }
    }
  }

  iftDestroyFHeap(&Q);
}

void remove_tree(Forest *F, iftImage *img, iftAdjRel *A, int root_p, iftSet **freed, iftSet **border_nodes) {
  iftSet *tree_copy = NULL;
  iftSet *it        = F->tree_nodes[root_p];
  while (it != NULL) {
    iftInsertSet(&tree_copy, it->elem);
    it = it->next;
  }

  char *in_freed = (char *) calloc(img->n, sizeof(char));

  while (tree_copy != NULL) {
    int p = iftRemoveSet(&tree_copy);

    F->cost->val[p]  = IFT_INFINITY_FLT;
    F->pred->val[p]  = IFT_NIL;
    F->root->val[p]  = p;
    F->label->val[p] = 0;
    iftInsertSet(freed, p);
    in_freed[p] = 1;
  }

  iftDestroySet(&F->tree_nodes[root_p]);
  F->tree_nodes[root_p] = NULL;

  iftSet *fr = *freed;
  while (fr != NULL) {
    int      p = fr->elem;
    iftVoxel u = iftGetVoxelCoord(img, p);

    for (int i = 1; i < A->n; i++) {
      iftVoxel v = iftGetAdjacentVoxel(A, u, i);
      if (!iftValidVoxel(img, v)) continue;

      int q = iftGetVoxelIndex(img, v);
      if (!in_freed[q] && F->cost->val[q] < IFT_INFINITY_FLT)
        iftInsertSet(border_nodes, q);
    }
    fr = fr->next;
  }

  free(in_freed);
}

void save_forest(Forest *F, const char *dir) {
  char path[1024];

  sprintf(path, "%s/cost.scn",  dir); write_fimage_scn(F->cost, path);
  sprintf(path, "%s/pred.scn",  dir); iftWriteImageByExt(F->pred,  path);
  sprintf(path, "%s/root.scn",  dir); iftWriteImageByExt(F->root,  path);
  sprintf(path, "%s/label.scn", dir); iftWriteImageByExt(F->label, path);
}

Forest *load_forest(const char *dir) {
  Forest *F = (Forest *) calloc(1, sizeof(Forest));
  char path[1024];

  sprintf(path, "%s/cost.scn",  dir); F->cost  = read_fimage_scn(path);
  sprintf(path, "%s/pred.scn",  dir); F->pred  = iftReadImageByExt(path);
  sprintf(path, "%s/root.scn",  dir); F->root  = iftReadImageByExt(path);
  sprintf(path, "%s/label.scn", dir); F->label = iftReadImageByExt(path);

  int n = F->label->n;
  F->tree_nodes = (iftSet **) calloc(n, sizeof(iftSet *));

  for (int p = 0; p < n; p++)
    iftInsertSet(&F->tree_nodes[F->root->val[p]], p);

  return F;
}

void destroy_forest(Forest **F, int n) {
  if (!F || !*F) return;
  iftDestroyFImage(&(*F)->cost);
  iftDestroyImage (&(*F)->pred);
  iftDestroyImage (&(*F)->root);
  iftDestroyImage (&(*F)->label);
  for (int p = 0; p < n; p++)
    if ((*F)->tree_nodes[p])
      iftDestroySet(&(*F)->tree_nodes[p]);
  free((*F)->tree_nodes);
  free(*F);
  *F = NULL;
}

void initial_loop(iftImage *img, iftAdjRel *A, iftImage *init_seg, const char *output_dir) {
  float  *G   = compute_gradient(img, A);
  Forest *F   = compute_mst(img, A, G);

  iftLabeledSet *seeds = recover_seeds(F, init_seg);

  run_ift(F, img, A, seeds, NULL, G, 1);

  char step_dir[1024];
  sprintf(step_dir, "%s/step-1", output_dir);
  iftMakeDir(step_dir);
  save_forest(F, step_dir);

  char path[1024];
  sprintf(path, "%s/step-1/label_out.scn", output_dir);
  iftWriteImageByExt(F->label, path);

  printf("Passo inicial concluido. Label salvo em %s\n", path);

  iftDestroyLabeledSet(&seeds);
  free(G);
  destroy_forest(&F, img->n);
}

void dift_loop(iftImage *img, iftAdjRel *A, float *G, const char *new_seeds_path, const char *prev_dir, const char *output_dir, int step) {
  Forest *F = load_forest(prev_dir);

  iftImage      *marker_img = iftReadImageByExt(new_seeds_path);
  iftLabeledSet *new_seeds  = NULL;

  for (int p = 0; p < marker_img->n; p++) {
    if (marker_img->val[p] > 0)
      iftInsertLabeledSet(&new_seeds, p, marker_img->val[p]);
  }
  iftDestroyImage(&marker_img);

  iftSet *freed        = NULL;
  iftSet *border_nodes = NULL;
  char   *removed      = (char *) calloc(img->n, sizeof(char));

  iftLabeledSet *s = new_seeds;
  while (s != NULL) {
    int p = s->elem;
    int r = F->root->val[p];

    if (!removed[r] && F->tree_nodes[r] != NULL) {
      remove_tree(F, img, A, r, &freed, &border_nodes);
      removed[r] = 1;
    }
    s = s->next;
  }
  free(removed);

  run_ift(F, img, A, new_seeds, border_nodes, G, 0);

  char step_dir[1024];
  sprintf(step_dir, "%s/step-%d", output_dir, step);
  iftMakeDir(step_dir);
  save_forest(F, step_dir);

  char path[1024];
  sprintf(path, "%s/step-%d/label_out.scn", output_dir, step);
  iftWriteImageByExt(F->label, path);

  printf("Passo %d concluido. Label salvo em %s\n", step, path);

  iftDestroyLabeledSet(&new_seeds);
  iftDestroySet(&freed);
  iftDestroySet(&border_nodes);
  destroy_forest(&F, img->n);
}

int main(int argc, char *argv[]) {

  if (argc != 4 && argc != 7) {
    fprintf(stderr,
      "Uso 1a iteracao : ./DIFT <img> <init_seg> <output_dir>\n"
      "Uso iteracoes   : ./DIFT <img> <init_seg> <output_dir>"
                        " <prev_dir> <new_markers.scn> <step_n>\n");
    return 1;
  }

  iftImage  *img      = iftReadImageByExt(argv[1]);
  iftImage  *init_seg = iftReadImageByExt(argv[2]);
  const char *out_dir = argv[3];
  iftAdjRel  *A       = iftSpheric(1.0f);

  if (argc == 4) {
    initial_loop(img, A, init_seg, out_dir);
  } else {
    const char *prev_dir    = argv[4];
    const char *markers_path = argv[5];
    int         step        = atoi(argv[6]);

    float *G = compute_gradient(img, A);
    dift_loop(img, A, G, markers_path, prev_dir, out_dir, step);
    free(G);
  }

  iftDestroyImage(&img);
  iftDestroyImage(&init_seg);
  iftDestroyAdjRel(&A);

  return 0;
}