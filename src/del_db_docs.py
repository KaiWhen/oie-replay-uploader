from mongo import scores_col

scores_col.delete_many({'uploaded': False})
