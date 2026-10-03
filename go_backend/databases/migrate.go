package database

import (
	"context"
	"fmt"
	"os"

	"github.com/jackc/pgx/v5/pgxpool"
)

func RunMigrations(
	ctx context.Context,
	pool *pgxpool.Pool,
) error {
	data, err := os.ReadFile(
		"migrations/001_init.sql",
	)

	if err != nil {
		return fmt.Errorf(
			"read migration: %w",
			err,
		)
	}

	if _, err := pool.Exec(
		ctx,
		string(data),
	); err != nil {
		return fmt.Errorf(
			"run migration: %w",
			err,
		)
	}

	return nil
}
