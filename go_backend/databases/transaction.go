package database

import (
	"context"
	"fmt"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
)

// WithTx chay fn ben trong mot PostgreSQL transaction.
//
// Neu fn thanh cong:
// BEGIN -> fn -> COMMIT
//
// Neu fn tra ve loi:
// BEGIN -> fn -> ROLLBACK
func WithTx(
	ctx context.Context,
	pool *pgxpool.Pool,
	fn func(pgx.Tx) error,
) error {
	tx, err := pool.Begin(ctx)
	if err != nil {
		return fmt.Errorf(
			"begin transaction: %w",
			err,
		)
	}

	// Neu transaction da commit thi Rollback se khong lam gi.
	// Neu co loi truoc commit thi no dam bao rollback.
	defer func() {
		_ = tx.Rollback(ctx)
	}()

	if err := fn(tx); err != nil {
		return err
	}

	if err := tx.Commit(ctx); err != nil {
		return fmt.Errorf(
			"commit transaction: %w",
			err,
		)
	}

	return nil
}
