#include "ift.h"

typedef struct {
  iftFImage *cost;
  iftImage *label;
  iftImage *root;
  iftImage *pred;
} MST;

MST *compute_mst(iftImage *img, iftAdjRel *A, iftLabeledSet *S) {
  MST *F = (MST*) malloc(sizeof(MST));

  F->cost  = iftCreateFImage(img->xsize, img->ysize, img->zsize);
  F->label = iftCreateImage(img->xsize, img->ysize, img->zsize);
  F->root  = iftCreateImage(img->xsize, img->ysize, img->zsize);
  F->pred  = iftCreateImage(img->xsize, img->ysize, img->zsize);

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
    seeds = seeds->next;
  }

  while (!iftEmptyFHeap(Q)) {
    int p = iftRemoveFHeap(Q);
    u = iftGetVoxelCoord(img,p);

    for (int i = 1; i < A->n; i++) {
      v = iftGetAdjacentVoxel(A, u, i);
      if (iftValidVoxel(img, v)) {
        q = iftGetVoxelIndex(img, v);
        if (F->cost->val[q] > F->cost->val[p]) {
          float w_pq = fabsf(img->val[p] - img->val[q]);
          float tmp = fmaxf((float)F->cost->val[p], w_pq);
  
          if (tmp < F->cost->val[q]) {
            F->cost->val[q] = tmp;
            F->root->val[q] = F->root->val[p];
            F->label->val[q] = F->label->val[p];
            F->pred->val[q] = p;

            if (Q->color[q] == IFT_WHITE)
              iftInsertFHeap(Q, q);
            else
              iftGoUpFHeap(Q, Q->pos[q]);
          }
        }
      }
    }
  }

  iftDestroyFHeap(&Q);

  return F;
}

iftSet *detect_leaks(MST *F, iftImage *img, iftAdjRel *A) {
  iftSet *leaks = NULL;
  iftVoxel u, v;
  int p, q;

  for (p = 0; p < img->n; p++) {
    u = iftGetVoxelCoord(img, p);

    for (int i = 1; i < A->n; i++) {
      v = iftGetAdjacentVoxel(A, u, i);

      if (iftValidVoxel(img, v)) {
        q = iftGetVoxelIndex(img, v);

        float w_pq = fabsf(img->val[q] - img->val[p]);
        float tmp = fmaxf(F->cost->val[q], w_pq);

        if (tmp < F->cost->val[p]) {
          iftInsertSet(&leaks, p);
          break;
        }
      }
    }
  }

  return leaks;
}

void remove_tree(MST *F, int root_p, int n, iftSet **affected) {
  for (int i = 0; i < n; i++) {
    if (F->root->val[i] == root_p) {
      F->cost->val[i] = IFT_INFINITY_FLT;
      F->pred->val[i] = IFT_NIL;
      iftInsertSet(affected, i);
    }
  }
}

void iterate_ift(MST *F, iftImage *img, iftAdjRel *A, iftSet *affected) {
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

        float w = fabsf(img->val[p] - img->val[q]);
        float tmp = fmaxf(F->cost->val[p], w);

        if (tmp < F->cost->val[q]) {
          F->cost->val[q] = tmp;
          F->pred->val[q] = p;
          F->root->val[q] = F->root->val[p];
          F->label->val[q] = F->label->val[p];

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

MST *DIFT(iftImage *img, iftAdjRel *A, iftLabeledSet *S, int max_iters) {
  MST *mst = compute_mst(img, A, S);

  for (int iter = 0; iter < max_iters; iter++) {

    iftSet *leaks = detect_leaks(mst, img, A);

    if (leaks == NULL) {
      break;
    }

    iftSet *affected = NULL;

    while (leaks != NULL) {
      int p = iftRemoveSet(&leaks);
      remove_tree(mst, mst->root->val[p], img->n, &affected);
    }

    iterate_ift(mst, img, A, affected);
  }

  return mst;
}

iftLabeledSet *convert_seeds(iftImage *label) {
  iftLabeledSet *S = NULL;

  for (int p = 0; p < label->n; p++) {
    int lb = label->val[p];

    if (lb != 0) {
      iftInsertLabeledSet(&S, p, lb);
    }
  }

  return S;
}

int main(int argc, char *argv[]) {
  if (argc != 4) {
    printf("Uso: ./DIFT [input_image_path] [label_path] [output_image_path]");
    exit(1);
  }

  iftImage *img = iftReadImage(argv[1]);
  iftWriteImageByExt(img, "output/test.scn");
  iftImage *label_init = iftReadImage(argv[2]);
  iftWriteImageByExt(label_init, "output/test_label.scn");

  iftAdjRel *A = iftSpheric(1.0);
  
  iftLabeledSet *S = convert_seeds(label_init);

  int max_iters = 10;

  MST *mst = DIFT(img, A, S, max_iters);

  iftWriteImageByExt(mst->label, argv[3]);

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