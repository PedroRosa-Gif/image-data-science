#include "ift.h"

typedef struct {
  iftFImage *cost;
  iftImage *label;
  iftImage *root;
  iftImage *pred;
  iftSet **tree_nodes;
} MST;

float *compute_gradient(iftImage *img, iftAdjRel *A) {
  float *G = (float *) calloc(img->n, sizeof(float));

  for (int p = 0; p < img->n; p++) {
    iftVoxel u = iftGetVoxelCoord(img, p);
    float sum = 0;
    int count = 0;

    for (int i = 1; i < A->n; i++) {
      iftVoxel v = iftGetAdjacentVoxel(A, u, i);
      if (iftValidVoxel(img, v)) {
        int q = iftGetVoxelIndex(img, v);
        sum += fabsf(img->val[p] - img->val[q]);
        count++;
      }
    }

    if (count > 0)
      G[p] = sum / count;
  }

  return G;
}

MST *compute_mst(iftImage *img, iftAdjRel *A, iftLabeledSet *S, float *G) {
  MST *F = (MST*) malloc(sizeof(MST));

  F->cost  = iftCreateFImage(img->xsize, img->ysize, img->zsize);
  F->label = iftCreateImage(img->xsize, img->ysize, img->zsize);
  F->root  = iftCreateImage(img->xsize, img->ysize, img->zsize);
  F->pred  = iftCreateImage(img->xsize, img->ysize, img->zsize);
  F->tree_nodes = calloc(img->n, sizeof(iftSet*));

  iftFHeap *Q = iftCreateFHeap(img->n, F->cost->val);
  iftLabeledSet *seeds = S;

  iftVoxel u, v;
  int p, q;

  for (p = 0; p < F->cost->n; p++) {
    F->cost->val[p] = IFT_INFINITY_FLT;
    F->root->val[p] = p;
    F->pred->val[p] = IFT_NIL;
  }

  while (seeds != NULL) {
    p = seeds->elem;
    F->cost->val[p] = 0;
    F->label->val[p] = seeds->label;
    
    iftInsertFHeap(Q, p);
    iftInsertSet(&F->tree_nodes[p], p);

    seeds = seeds->next;
  }

  while (!iftEmptyFHeap(Q)) {
    int p = iftRemoveFHeap(Q);
    u = iftGetVoxelCoord(img,p);

    for (int i = 1; i < A->n; i++) {
      v = iftGetAdjacentVoxel(A, u, i);
      if (iftValidVoxel(img, v)) {
        q = iftGetVoxelIndex(img, v);

        float w = (G[p] + G[q]) / 2.0f;
        float tmp = fmaxf(F->cost->val[p], w);

        if (tmp < F->cost->val[q]) {
          F->cost->val[q] = tmp;
          F->root->val[q] = F->root->val[p];
          F->label->val[q] = F->label->val[p];
          F->pred->val[q] = p;

          iftInsertSet(&F->tree_nodes[F->root->val[q]], q);

          if (Q->color[q] == IFT_WHITE)
            iftInsertFHeap(Q, q);
          else
            iftGoUpFHeap(Q, Q->pos[q]);
        }
      }
    }
  }

  iftDestroyFHeap(&Q);
  return F;
}

// iftSet *detect_leaks(MST *F, iftAdjRel *A, float *G) {
//   iftSet *leaks = NULL;
//   int count = 0;

//   for (int p = 0; p < F->label->n; p++) {
//     if (F->label->val[p] == 0) continue;

//     iftVoxel u = iftGetVoxelCoord(F->label, p);

//     for (int i = 1; i < A->n; i++) {
//       iftVoxel v = iftGetAdjacentVoxel(A, u, i);

//       if (iftValidVoxel(F->label, v)) {
//         int q = iftGetVoxelIndex(F->label, v);

//         if (F->label->val[q] != F->label->val[p]) {
//           iftInsertSet(&leaks, p);
//           count++;
//           break;
//         }
//       }
//     }
//   }

//   printf("Numero de leaks: %d\n", count);
//   return leaks;
// }

iftSet *detect_leaks(MST *F, iftAdjRel *A, float *G, float threshold) {
  iftSet *leaks = NULL;
  int count = 0;

  for (int p = 0; p < F->label->n; p++) {
    if (F->label->val[p] == 0) continue;
    iftVoxel u = iftGetVoxelCoord(F->label, p);
    
    for (int i = 1; i < A->n; i++) {
      iftVoxel v = iftGetAdjacentVoxel(A, u, i);
      if (iftValidVoxel(F->label, v)) {
        int q = iftGetVoxelIndex(F->label, v);
        if (F->label->val[q] != F->label->val[p] && G[p] < threshold) {
          iftInsertSet(&leaks, p);
          count++;
          break;
        }
      }
    }
  }

  printf("Numero de leaks: %d\n", count);
  return leaks;
}

void remove_tree(MST *F, int root_p, iftSet **affected) {
  iftSet *S = F->tree_nodes[root_p];

  while (S != NULL) {
    int p = iftRemoveSet(&S);

    F->cost->val[p] = IFT_INFINITY_FLT;
    F->pred->val[p] = IFT_NIL;
    F->root->val[p] = p;
    F->label->val[p] = 0;

    iftInsertSet(affected, p);
  }

  F->tree_nodes[root_p] = NULL;
}

void iterate_ift(MST *F, iftImage *img, iftAdjRel *A, iftSet *affected, float *G) {
  iftFHeap *Q = iftCreateFHeap(img->n, F->cost->val);

  int p, q;
  iftVoxel u, v;

  while (affected != NULL) {
    p = iftRemoveSet(&affected);
    iftInsertFHeap(Q, p);
  }

  while (!iftEmptyFHeap(Q)) {
    p = iftRemoveFHeap(Q);
    u = iftGetVoxelCoord(img, p);

    for (int i = 1; i < A->n; i++) {
      v = iftGetAdjacentVoxel(A, u, i);

      if (iftValidVoxel(img, v)) {
        q = iftGetVoxelIndex(img, v);

        float w = (G[p] + G[q]) / 2.0f;
        float tmp = fmaxf(F->cost->val[p], w);

        if (tmp < F->cost->val[q]) {
          F->cost->val[q] = tmp;
          F->pred->val[q] = p;
          F->root->val[q] = F->root->val[p];
          F->label->val[q] = F->label->val[p];

          iftInsertSet(&F->tree_nodes[F->root->val[q]], q);

          if (Q->color[q] == IFT_WHITE)
            iftInsertFHeap(Q, q);
          else
            iftGoUpFHeap(Q, Q->pos[q]);
        }
      }
    }
  }

  iftDestroyFHeap(&Q);
}

MST *DIFT(iftImage *img, iftAdjRel *A, iftLabeledSet *S, int max_iters, char* output_path) {
  char filename[512];
  float *G = compute_gradient(img, A);
  MST *mst = compute_mst(img, A, S, G);

  sprintf(filename, "%s/mst.scn", output_path);
  iftWriteImageByExt(mst->label, filename);

  for (int iter = 0; iter < max_iters; iter++) {
    printf("Processing image %d...\n", (iter + 1));

    iftSet *leaks = detect_leaks(mst, A, G, 2500.0);

    if (leaks == NULL) {
      break;
    }

    iftSet *affected = NULL;
    char *visited_roots = (char *) calloc(img->n, sizeof(char));
    int count = 1;
    
    while (leaks != NULL) {
      int p = iftRemoveSet(&leaks);
      int root_p = mst->root->val[p];

      if (!visited_roots[root_p]) {
        remove_tree(mst, root_p, &affected);
        visited_roots[root_p] = 1;
      }

      if (count % 10000 == 0) {
        printf("%d processados\n", count);
      }
      count++;
    }

    iterate_ift(mst, img, A, affected, G);

    sprintf(filename, "%s/seg-step-%d.scn", output_path, iter + 1);
    iftWriteImageByExt(mst->label, filename);
  }

  return mst;
}

iftLabeledSet *convert_seeds(iftImage *label) {
  iftLabeledSet *S = NULL;

  for (int p = 0; p < label->n; p++) {
    int lb = label->val[p];
    iftInsertLabeledSet(&S, p, lb);
  }

  return S;
}

int main(int argc, char *argv[]) {
  if (argc < 4 || argc > 5) {
    printf("Uso: ./DIFT [input_image_path] [label_path] [output_image_path] [ui_mode]");
    exit(1);
  }

  iftImage *img = iftReadImage(argv[1]);
  iftImage *label_init = iftReadImage(argv[2]);

  iftAdjRel *A = iftSpheric(1.0);
  
  iftLabeledSet *S = convert_seeds(label_init);

  int max_iters = 10;

  if (argc == 5)
    max_iters = 1;

  MST *mst = DIFT(img, A, S, max_iters, argv[3]);

  iftDestroyImage(&img);
  iftDestroyImage(&label_init);
  iftDestroyAdjRel(&A);
  iftDestroyLabeledSet(&S);
  iftDestroyFImage(&mst->cost);
  iftDestroyImage(&mst->label);
  iftDestroyImage(&mst->root);
  iftDestroyImage(&mst->pred);

  return 0;
}